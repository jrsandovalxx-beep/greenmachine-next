"""GMF-006 hotfix regressions: the deployed board must render with missing data.

Two deployed failure classes, both reproduced against the deployed runtime
(Python 3.14 / pandas 3) before these tests were written:

1. A batter with no Statcast or form row leaves ``None`` cells in the Sluggers
   frame; pandas stores them as NaN, and ``Decimal('NaN') >= edge`` raises
   ``decimal.InvalidOperation`` inside the highlight mapper — killing the whole
   script run at the first tab (D-075 isolates the tabs now).
2. The parks screen bound the live NWS adapter but declared only the fixture
   sources, so the contract rejected the snapshot with ``InputContractError``.

The board here is built through the real ``build_board`` with one batter
covered by every feed and one missed by all of them — the exact mixed-column
cell pattern the deployed slate produced.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from greenmachine.config.loader import load_config
from greenmachine.inputs.contract import Handedness, ParkFactor
from greenmachine.live.mlb_api import (
    BattingOrders,
    FetchFailure,
    ProbablePitcher,
    ScheduledGame,
    SeasonHittingLine,
    SeasonPitchingLine,
    Slate,
)
from greenmachine.live.pipeline import SlateBoard, build_board
from greenmachine.live.savant import BatTrackingRow, StatcastBatterRow

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(REPO_ROOT / "config" / "production" / "gm_hr_v1.yaml")
SLATE_DATE = date(2026, 8, 20)
AS_OF = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)
BATTER_ID = 101
BATTER_ID_2 = 102  # the batter every feed missed — the None cells
PITCHER_ID = 201

_APP_PATH = REPO_ROOT / "streamlit_app.py"
_TIMEOUT = 60


def _game() -> ScheduledGame:
    return ScheduledGame(
        game_pk=777001,
        official_date="2026-08-20",
        game_datetime_utc="2026-08-21T01:40:00Z",
        status="Scheduled",
        venue_id=15,
        venue_name="Chase Field",
        home_team="Arizona Diamondbacks",
        away_team="Los Angeles Dodgers",
        home_probable=ProbablePitcher(player_id=PITCHER_ID, full_name="Ace Righty"),
        away_probable=None,
    )


class _OutageApi:
    """A slate and posted orders, but a season line for only one batter."""

    def fetch_slate(self, date_mmddyyyy: str) -> Slate:
        return Slate(official_date="2026-08-20", games=(_game(),))

    def fetch_batting_orders(self, game_pk: int) -> BattingOrders:
        return BattingOrders(
            game_pk=game_pk, home=(BATTER_ID, BATTER_ID_2), away=(BATTER_ID, BATTER_ID_2)
        )

    def fetch_season_hitting(self, player_ids: tuple[int, ...]) -> dict[int, SeasonHittingLine]:
        return {
            BATTER_ID: SeasonHittingLine(
                player_id=BATTER_ID,
                full_name="Covered Batter",
                bats="L",
                games=120,
                plate_appearances=500,
                at_bats=440,
                hits=121,
                home_runs=33,
                strikeouts=130,
            )
        }

    def fetch_season_pitching(self, player_ids: tuple[int, ...]) -> dict[int, SeasonPitchingLine]:
        return {
            PITCHER_ID: SeasonPitchingLine(
                player_id=PITCHER_ID,
                full_name="Ace Righty",
                throws="R",
                games_started=25,
                innings_pitched="150.1",
                era="3.10",
                whip="1.05",
                strikeouts=190,
                batters_faced=620,
            )
        }


class _OutageSavant:
    """One batter covered, one not: the mix that turns a column float64 and
    stores the missing cells as NaN — the deployed crash's raw material."""

    def fetch_pitch_arsenal(self, *, kind: str, year: int) -> tuple:
        return ()

    def fetch_statcast_batters(self, *, year: int, minimum: int = 0) -> dict:
        return {
            BATTER_ID: StatcastBatterRow(
                player_id=BATTER_ID,
                batted_ball_events=300,
                exit_velocity_avg=Decimal("91.5"),
                hard_hit_count=150,
                hard_hit_share=Decimal("0.5"),
                barrel_count=30,
                barrel_share=Decimal("0.1"),
                sweet_spot_share=Decimal("0.33"),
            )
        }

    def fetch_bat_tracking(self, *, year: int, minimum: int = 0, start: str = "", end: str = ""):
        return (
            BatTrackingRow(
                player_id=BATTER_ID,
                side="L",
                avg_bat_speed=Decimal("74"),
                attack_angle=Decimal("12"),
                ideal_attack_angle_share=Decimal("0.6"),
                competitive_swings=300,
            ),
        )


def _outage_board() -> SlateBoard:
    """A real board build in which every metric feed failed."""
    board = build_board(
        api=_OutageApi(),  # type: ignore[arg-type]
        savant=_OutageSavant(),  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        fetch_day_events=lambda day: FetchFailure("simulated outage"),  # type: ignore[arg-type]
        temperature_for=lambda venue: None,  # type: ignore[arg-type]
        park_factors={
            15: {
                Handedness.LEFT: ParkFactor(
                    factor=Decimal("112"), handedness=Handedness.LEFT, plate_appearances=30000
                ),
                Handedness.RIGHT: ParkFactor(
                    factor=Decimal("98"), handedness=Handedness.RIGHT, plate_appearances=30000
                ),
            }
        },
    )
    assert isinstance(board, SlateBoard)
    batters = board.games[0].home_batters + board.games[0].away_batters
    assert batters, "the board must still carry lineup batters"
    # The crash condition: a column mixing real values with missing ones.
    assert any(card.statcast is None for card in batters)
    assert any(card.statcast is not None for card in batters)
    return board


@pytest.fixture
def _staged_app(monkeypatch: pytest.MonkeyPatch) -> SlateBoard:
    """The app in its deployed posture, with the outage board and no network."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline
    from greenmachine.inputs import AbsenceReason, SnapshotField, WeatherForecast
    from greenmachine.weather.nws import SOURCE_ID, NwsWeatherAdapter

    board = _outage_board()
    monkeypatch.setattr(pipeline, "build_board", lambda **kwargs: board)
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    monkeypatch.setattr(
        NwsWeatherAdapter,
        "forecast_for",
        lambda self, venue: SnapshotField[WeatherForecast].absent(
            AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
        ),
    )
    st.cache_data.clear()
    return board


def test_all_four_tabs_render_with_every_metric_missing(_staged_app: SlateBoard) -> None:
    """The deployed crash: NaN cells reached the highlight styling. The main
    screen — shell plus the board's four tabs — renders with zero exceptions."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    labels = [tab.label for tab in at.tabs]
    assert labels == ["Sluggers", "Arms", "Matchups", "Conditions"]
    assert len(at.dataframe) >= 3  # sluggers, arms, conditions at minimum


def _display_values(element: object) -> pd.DataFrame:
    """A Styler-backed dataframe's shown text, from the Arrow display payload.

    The proto forked inside the Streamlit version bound (see the grid tests'
    `_arrow_surface`): resolve the Arrow message first, then read its styler.
    """
    import io

    import pyarrow as pa

    proto = element.proto  # type: ignore[attr-defined]
    if "arrow_data" in {f.name for f in proto.DESCRIPTOR.fields}:
        proto = proto.arrow_data
    return pa.ipc.open_stream(io.BytesIO(proto.styler.display_values)).read_all().to_pandas()


def test_missing_cells_name_their_reason(_staged_app: SlateBoard) -> None:
    """D-023/D-025 on the live surface: a missing metric is its reason in
    words — never a blank, a zero, or the literal string 'None'."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    display = _display_values(at.dataframe[0]).astype(str)
    assert not display.isin(["None", "nan"]).any().any()
    # The uncovered batter's cells carry the board's plain-language reasons.
    cells = set(display.to_numpy().ravel())
    assert "not covered by source" in cells


def test_main_screen_is_the_shell_plus_the_live_board(_staged_app: SlateBoard) -> None:
    """D-076: the main screen is the Xbox shell and the live board — the demo
    surfaces (batter grid, metrics, parks) are not on it — and the GMR-004
    deployment-verification fields survive in the header's status line."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    subheaders = [element.value for element in at.subheader]
    assert "Batter grid" not in subheaders
    assert "Parks" not in subheaders
    # No demo choosers, and no ranking control anywhere (D-015/D-017).
    assert not at.selectbox
    assert not at.multiselect
    assert not at.radio
    markup = "\n".join(element.value for element in at.markdown)
    assert "gm-orb" in markup
    assert "ENVIRONMENT staging" in markup
    assert "VERSION" in markup
    assert "COMMIT" in markup
    assert [tab.label for tab in at.tabs] == ["Sluggers", "Arms", "Matchups", "Conditions"]


def test_one_tabs_failure_cannot_blank_the_rest(tmp_path: Path) -> None:
    """D-075: a tab that raises degrades to a named warning; the other tab and
    every section after the board still render. Driven through a minimal script
    so the real ``_render_tab`` helper runs inside a genuine app runtime."""
    script = tmp_path / "isolation_app.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "import streamlit as st\n"
        "from streamlit_app import _render_tab\n"
        "\n"
        "def _boom():\n"
        "    raise RuntimeError('synthetic render failure')\n"
        "\n"
        "first, second = st.tabs(['A', 'B'])\n"
        "with first:\n"
        "    _render_tab('A', _boom)\n"
        "with second:\n"
        "    _render_tab('B', lambda: st.dataframe({'x': [1]}))\n"
        "st.dataframe({'after': [2]})\n"
    )
    at = AppTest.from_file(str(script), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any("A" in str(w.value) for w in at.warning)
    assert len(at.dataframe) == 2  # the surviving tab and the section after


def test_parks_snapshot_declares_a_live_weather_source() -> None:
    """The deployed parks crash: a live adapter's fields name its own source,
    so the snapshot must declare it or the contract rejects the page."""
    from greenmachine.fixtures import parks_demo_snapshot
    from greenmachine.inputs import AbsenceReason, SnapshotField, WeatherForecast
    from greenmachine.weather.nws import SOURCE, SOURCE_ID

    class _LiveStub:
        source = SOURCE

        def forecast_for(self, venue):
            return SnapshotField[WeatherForecast].absent(
                AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
            )

    snapshot = parks_demo_snapshot(_LiveStub())  # type: ignore[arg-type]
    assert SOURCE in snapshot.sources


def test_slugger_frames_carry_value_reason_and_highlight() -> None:
    """The live board's frame is uniformly textual: the data grid prints a
    numeric null as the literal "None" whatever the styler says (D-076), so
    the value or its reason IS the cell's text, and the style frame carries
    the green highlight decided at build time — no NaN is ever compared."""
    import streamlit_app

    board = _outage_board()
    texts, styles = streamlit_app._slugger_frames(board, {"EV": Decimal("90")})
    # Row 0 is the covered batter (EV 91.5 ≥ 90): the formatted value, green.
    assert texts.at[0, "EV"] == "91.5"
    assert styles.at[0, "EV"] == streamlit_app._HIGHLIGHT
    # Row 1 is the batter every feed missed: the reason as the cell's text,
    # muted styling.
    assert texts.at[1, "EV"] == "not covered by source"
    assert styles.at[1, "EV"] == streamlit_app._REASON_CSS
