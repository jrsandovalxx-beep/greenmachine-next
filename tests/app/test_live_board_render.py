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
    """The deployed crash: NaN cells reached the highlight mapper. The whole
    page must render — tabs, grid, metrics, parks — with zero exceptions."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    labels = [tab.label for tab in at.tabs]
    assert labels == ["Sluggers", "Arms", "Matchups", "Conditions"]
    assert len(at.dataframe) >= 3  # sluggers, arms, conditions at minimum


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


def test_highlight_mapper_treats_non_numeric_cells_as_unhighlighted() -> None:
    """NaN, None, pd.NA and text all map to 'no highlight'; a genuine value at
    the edge still turns green. Forcing the Styler to compute is the test."""
    import pandas as pd
    import streamlit_app

    frame = pd.DataFrame(
        {"Batter": ["a", "b", "c", "d", "e"], "EV": [float("nan"), None, "n/a", 96.2, 90.0]}
    )
    styler = streamlit_app._highlight_columns(frame, {"EV": Decimal("95")})
    computed = styler._compute()
    styles = computed.ctx  # {(row, col): [("background-color", ...)]}
    assert styles.get((3, 1)) == [("background-color", "#d4edda")]
    assert all(styles.get((row, 1)) is None for row in (0, 1, 2, 4))
