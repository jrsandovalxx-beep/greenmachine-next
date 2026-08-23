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

from datetime import UTC, date, datetime, timedelta
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
    GameLogEntry,
    MlbStatsApi,
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

    def fetch_recent_game_logs(
        self, player_ids: tuple[int, ...], start_mmddyyyy: str, end_mmddyyyy: str
    ) -> FetchFailure:
        return FetchFailure("game-logs: simulated outage")


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

    def fetch_expected_stats(self, *, year: int) -> dict:
        return {}

    def fetch_sprint_speed(self, *, year: int) -> dict:
        return {}

    def fetch_squared_up(self, *, year: int, minimum: int = 0) -> dict:
        return {}


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


def _graded_board() -> SlateBoard:
    """The outage board with grades set S, A, B, D across its four cards —
    the D-084 shortlist must keep exactly the first two."""
    import dataclasses

    from greenmachine.domain.enums import Grade
    from greenmachine.domain.grade_result import EvaluatedGradeResult
    from greenmachine.live.pipeline import BatterCard, GameCard

    board = _outage_board()
    grades = [Grade.S, Grade.A, Grade.B, Grade.D]

    def regrade(cards: tuple[BatterCard, ...]) -> tuple[BatterCard, ...]:
        out: list[BatterCard] = []
        for card in cards:
            grade = grades.pop(0) if grades else Grade.D
            result = card.result
            assert isinstance(result, EvaluatedGradeResult)
            out.append(dataclasses.replace(card, result=dataclasses.replace(result, grade=grade)))
        return tuple(out)

    game = board.games[0]
    regraded = dataclasses.replace(
        game, home_batters=regrade(game.home_batters), away_batters=regrade(game.away_batters)
    )
    assert isinstance(regraded, GameCard)
    return dataclasses.replace(board, games=(regraded, *board.games[1:]))


@pytest.fixture
def _staged_app(monkeypatch: pytest.MonkeyPatch) -> SlateBoard:
    """The app in its deployed posture, with the graded outage board and no
    network."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline
    from greenmachine.inputs import AbsenceReason, SnapshotField, WeatherForecast
    from greenmachine.weather.nws import SOURCE_ID, NwsWeatherAdapter

    board = _graded_board()
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
    words — never a blank, a zero, or the literal string 'None'. On the
    D-084 shortlist those reasons ride in the tags box."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    display = _display_values(at.dataframe[0]).astype(str)
    assert not display.isin(["None", "nan"]).any().any()
    # The uncovered shortlist batter's tags name the absences in words.
    tags = " ".join(display["Tags"].tolist()).lower()
    assert "missing:" in tags
    assert "source unavailable" in tags


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


def test_shortlist_keeps_only_a_and_s_with_the_d084_columns() -> None:
    """D-084: the Sluggers tab is the shortlist — grades A and S only, and
    exactly the shortlist columns; every cell is display text (D-076), the
    grade is lit, and the cards stay row-aligned for selection (GMF-007)."""
    import streamlit_app

    texts, styles, cards = streamlit_app._slugger_frames(_graded_board())
    assert list(texts.columns) == [
        "Batter",
        "HR",
        "Team",
        "Versus",
        "Grade",
        "Park factor",
        "Weather",
        "Tags",
    ]
    # D-094: the outage board fetched no events, so no batter has a last
    # game day at all and the money-tag column stays blank — never a guess.
    assert texts["HR"].tolist() == ["", ""]
    assert list(texts["Grade"]) == ["S", "A"]
    assert styles["Grade"].tolist() == [streamlit_app._HIGHLIGHT] * 2
    # Park factor formatted as the whole-number factor for the batting side.
    assert texts["Park factor"].isin(["112", "98", "not covered"]).all()
    # The outage venue is roofed: the weather cell says so, in words.
    assert set(texts["Weather"]) == {"roofed — indoor neutral value"}
    # The third return is the card behind each row, in row order (GMF-007).
    assert [card.full_name for card in cards] == list(texts["Batter"])


def test_money_tag_marks_a_batter_who_homered() -> None:
    """D-094: a neon "$" sits beside a shortlist batter whose record holds a
    home run on or before the slate; a batter without one stays blank."""
    import dataclasses

    import pandas as _pd
    import streamlit_app

    board = _graded_board()
    game = board.games[0]
    tagged = dataclasses.replace(game.home_batters[0], homered_on_last_game_day=True)
    game = dataclasses.replace(game, home_batters=(tagged, *game.home_batters[1:]))
    board = dataclasses.replace(board, games=(game, *board.games[1:]))
    texts, styles, _cards = streamlit_app._slugger_frames(board)
    assert texts["HR"].tolist() == ["$", ""]
    assert styles["HR"].iloc[0] == streamlit_app._MONEY_CSS
    assert _pd.isna(styles["HR"].iloc[1])


def test_shortlist_empty_when_nothing_grades_a_or_s() -> None:
    """All-D slate: the shortlist is empty and the tab says so plainly."""
    import streamlit_app

    texts, _styles, cards = streamlit_app._slugger_frames(_outage_board())
    assert texts.empty
    assert cards == []


def _pitch_event(**overrides: object) -> object:
    from greenmachine.live.savant import PitchEvent

    base = {
        "game_pk": 777000,
        "game_date": "2026-08-19",
        "batter_id": 1,
        "pitcher_id": 2,
        "batter_side": "L",
        "pitcher_throws": "R",
        "pitch_type": "FF",
        "event": "field_out",
        "description": "",
        "bb_type": "fly_ball",
        "launch_speed": Decimal("91.2"),
        "launch_angle": Decimal("24"),
        "launch_speed_angle": 3,
        "hc_x": None,
        "hc_y": None,
        "estimated_woba": None,
        "woba_value": None,
        "woba_denom": None,
        "hit_distance": Decimal("360"),
    }
    base.update(overrides)
    return PitchEvent(**base)  # type: ignore[arg-type]


def test_exit_velo_log_lists_pa_ending_pitches_with_heat_and_hr_marks() -> None:
    """D-086: one row per plate-appearance-ending pitch — mid-PA pitches are
    not logged; a home run's event cell is lit; a hot EV carries the heat."""
    from types import SimpleNamespace

    import streamlit_app

    events = (
        _pitch_event(),  # FF fly out at 91.2, 360 ft
        _pitch_event(event="home_run", launch_speed=Decimal("104.1"), pitch_type="SL"),
        _pitch_event(event="", launch_speed=None, launch_angle=None),  # taken pitch
        _pitch_event(
            event="strikeout",
            launch_speed=None,
            launch_angle=None,
            hit_distance=None,
            pitch_type="CH",
        ),
    )
    card = SimpleNamespace(recent_events=events)
    texts, styles = streamlit_app._exit_velo_frames(card, False, 0.15)
    assert len(texts) == 3  # the taken pitch is not a row
    assert list(texts.columns) == ["Date", "Pitch", "Event", "EV", "LA", "Dist", "Type"]
    assert texts.at[0, "EV"] == "91.2"
    assert texts.at[0, "Type"] == "FB"
    assert texts.at[0, "Dist"] == "360"  # D-091: the hit's projected distance
    assert texts.at[2, "Dist"] == "—"  # a strikeout carries no reading
    assert texts.at[1, "Event"] == "HR"
    assert styles.at[1, "Event"] == streamlit_app._HR_CSS
    assert styles.at[1, "EV"] == streamlit_app._EV_HEAT[0][1]  # 104.1 is the hottest band
    # A strikeout is a logged outcome with no contact reading.
    assert texts.at[2, "Event"] == "Strikeout"
    assert texts.at[2, "EV"] == "—"


def test_exit_velo_threshold_filters_the_log_to_the_qualifying_mix() -> None:
    """D-086: the toggle filters the log's rows by pitch type — off keeps
    every pitch; on keeps only the window's qualifying pitch mix (≥15%)."""
    from types import SimpleNamespace

    import streamlit_app

    events = tuple(
        [_pitch_event(pitch_type="FF") for _ in range(7)]
        + [_pitch_event(pitch_type="SL") for _ in range(2)]
        + [_pitch_event(pitch_type="CH")]
    )
    card = SimpleNamespace(recent_events=events)
    texts_off, _ = streamlit_app._exit_velo_frames(card, False, 0.15)
    texts_on, _ = streamlit_app._exit_velo_frames(card, True, 0.15)
    assert set(texts_off["Pitch"]) == {"FF", "SL", "CH"}
    # CH at 10% of the window is below the qualifying share: its rows leave.
    assert set(texts_on["Pitch"]) == {"FF", "SL"}


def _pitch_line(**overrides: object) -> object:
    from greenmachine.live.pipeline import PitchLine

    base = {
        "pitch_type": "FF",
        "pitch_name": "4-Seam Fastball",
        "pitches": 60,
        "usage_share": Decimal("0.30"),
        "plate_appearances": 15,
        "batting_average": Decimal("0.280"),
        "slugging": Decimal("0.520"),
        "iso": Decimal("0.240"),
        "home_runs": 2,
        "barrel_share": Decimal("0.10"),
        "hard_hit_share": Decimal("0.45"),
        "expected_woba": Decimal("0.355"),
        "whiff_share": Decimal("0.24"),
    }
    base.update(overrides)
    return PitchLine(**base)  # type: ignore[arg-type]


def _season_line(**overrides: object) -> object:
    from greenmachine.live.pipeline import PitchLine

    base = {
        "pitch_type": "FF",
        "pitch_name": "4-Seam Fastball",
        "pitches": 400,
        "usage_share": Decimal("0.45"),
        "plate_appearances": 100,
        "batting_average": Decimal("0.250"),
        "slugging": Decimal("0.400"),
        "iso": Decimal("0.150"),
        "home_runs": None,
        "barrel_share": None,
        "hard_hit_share": Decimal("0.40"),
        "expected_woba": Decimal("0.300"),
        "whiff_share": Decimal("0.24"),
        "woba": Decimal("0.310"),
        "strikeout_share": Decimal("0.22"),
    }
    base.update(overrides)
    return PitchLine(**base)  # type: ignore[arg-type]


def test_breakup_table_pairs_pitcher_season_with_batter_window() -> None:
    """D-106: one table, two halves under an opaque sub-header — Usage% is
    the pitcher's season share (the batter's seen-share never appears), the
    first half is his season-long figures, the second the batter's window
    line against that exact pitch, and a below-threshold row dims."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(
        season_lines=(
            _season_line(),
            _season_line(pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.08")),
        )
    )
    batter_lines = (
        _pitch_line(),
        _pitch_line(pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.08")),
    )
    markup = streamlit_app._arsenal_breakup_html(
        pitcher,
        batter_lines,
        threshold=0.15,
        side_filter=None,
        side_usage=None,
        window_label="last month",
        throws_text="right",
    )
    assert "Pitcher — season" in markup
    assert "Batter — last month vs right-handed pitching" in markup
    assert "gm-half-boundary" in markup
    # Usage is the season board's — never the batter's seen share.
    assert ">45.0%<" in markup
    # Season-only columns (wOBA, K%) show; the batter half carries his HRs.
    assert ">.310<" in markup
    assert ">22.0%<" in markup
    assert ">2</td>" in markup
    # The 8%-usage changeup is below the qualifying share: dimmed, still listed.
    assert markup.count('class="gm-dim"') == 1
    assert "Changeup" in markup


def test_breakup_table_dashes_a_pitch_the_batter_has_not_seen() -> None:
    """D-106: a pitch in his arsenal the batter never saw from this side
    keeps its row — zero plate appearances and dashed rates, never hidden."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(
        season_lines=(
            _season_line(),
            _season_line(pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.20")),
        )
    )
    markup = streamlit_app._arsenal_breakup_html(
        pitcher,
        (_pitch_line(),),  # the batter's window holds fastballs only
        threshold=0.15,
        side_filter=None,
        side_usage=None,
        window_label="last 2 weeks",
        throws_text="right",
    )
    assert "Batter — last 2 weeks" in markup
    changeup_row = markup.split("Changeup", 1)[1].split("</tr>", 1)[0]
    assert '<td class="gm-half-boundary">0</td>' in changeup_row
    assert changeup_row.count("<td>—</td>") == 10


def test_breakup_side_toggle_switches_usage_to_the_hitter_hand_basis() -> None:
    """D-102 survives the merge: with the side toggle on, Usage% is his
    share of pitches to that hitter hand over the recent window, rows order
    by the shown basis and dim against it, and every other number stays
    season-long."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(
        season_lines=(
            _season_line(),  # FF, 45% season usage
            _season_line(pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.20")),
        )
    )
    side_usage = {"FF": Decimal("0.30"), "CH": Decimal("0.70")}
    markup = streamlit_app._arsenal_breakup_html(
        pitcher,
        (),
        threshold=0.15,
        side_filter=frozenset({"FF", "CH"}),
        side_usage=side_usage,
        window_label="last month",
        throws_text="right",
    )
    # The changeup leads vs this hand, so its row sorts first at 70%.
    assert markup.index("Changeup") < markup.index("4-Seam Fastball")
    assert ">70.0%<" in markup
    assert ">30.0%<" in markup
    assert ">45.0%<" not in markup
    # Every other number stays the season board's.
    assert "<td>100</td>" in markup
    assert ">.310<" in markup
    # The threshold dims on the shown basis: past 30%, the fastball dims
    # even though its season usage is 45%.
    markup_high = streamlit_app._arsenal_breakup_html(
        pitcher,
        (),
        threshold=0.45,
        side_filter=frozenset({"FF", "CH"}),
        side_usage=side_usage,
        window_label="last month",
        throws_text="right",
    )
    assert markup_high.count('class="gm-dim"') == 1
    dimmed = markup_high.split('class="gm-dim"', 1)[1].split("</tr>", 1)[0]
    assert "4-Seam Fastball" in dimmed


def test_breakup_side_filter_drops_rows_and_can_empty_the_table() -> None:
    """D-105/D-106: the side filter lists only the pitches he threw to this
    side; when none of them made his arsenal board the builder returns "" so
    the surface names the reason instead of rendering a blank grid."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(season_lines=(_season_line(),))
    markup = streamlit_app._arsenal_breakup_html(
        pitcher,
        (),
        threshold=0.15,
        side_filter=frozenset({"FF"}),
        side_usage=None,
        window_label="last month",
        throws_text="right",
    )
    assert "4-Seam Fastball" in markup
    empty = streamlit_app._arsenal_breakup_html(
        pitcher,
        (),
        threshold=0.15,
        side_filter=frozenset({"SL"}),  # thrown to this side, never on his board
        side_usage=None,
        window_label="last month",
        throws_text="right",
    )
    assert empty == ""


def test_arsenal_side_note_names_a_no_op_filter() -> None:
    """D-099: when he threw every pitch to this side, the toggle says so —
    a silent no-op reads as broken (the Weathers case); partial coverage
    filters quietly; an empty record names the fallback."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(
        season_lines=(
            _season_line(),
            _season_line(pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.20")),
        )
    )
    note = streamlit_app._arsenal_side_note(pitcher, frozenset({"FF", "CH"}), "right")
    assert "nothing to filter" in note
    assert streamlit_app._arsenal_side_note(pitcher, frozenset({"FF"}), "right") == ""
    assert "full arsenal" in streamlit_app._arsenal_side_note(pitcher, frozenset(), "right")


def test_a_dialog_failure_cannot_blank_the_board(tmp_path: Path) -> None:
    """D-075, extended to the detail dialog: if the dialog body raises, the
    run survives with a named warning and the board stays rendered. Drives
    the real ``_open_batter_detail`` guard inside a genuine app runtime."""
    script = tmp_path / "dialog_guard_app.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "import streamlit as st\n"
        "import streamlit_app\n"
        "\n"
        "def _boom(card, game):\n"
        "    raise RuntimeError('synthetic dialog failure')\n"
        "\n"
        "streamlit_app._batter_detail_dialog = _boom\n"
        "streamlit_app._open_batter_detail(object(), None)\n"
        "st.dataframe({'board': [1]})\n"
    )
    at = AppTest.from_file(str(script), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any("batter detail" in str(w.value) for w in at.warning)
    assert len(at.dataframe) == 1


def _grid_line(**overrides: object) -> object:
    from greenmachine.live.pipeline import BatterGridLine

    base = {
        "pitches": 22,
        "plate_appearances": 6,
        "at_bats": 5,
        "hits": 2,
        "batted_balls": 4,
        "barrels": 1,
        "home_runs": 1,
        "exit_velocity": Decimal("95.5"),
        "barrel_per_pa": Decimal("0.1667"),
        "hard_hit_share": Decimal("0.5"),
        "batting_average": Decimal("0.4"),
        "slugging": Decimal("1.0"),
        "iso": Decimal("0.6"),
        "distance_350_count": 1,
        "pull_air_share": Decimal("0.4"),
        "oppo_air_share": Decimal("0.25"),
        "expected_woba": Decimal("0.45"),
        "whiff_share": Decimal("0.12"),
    }
    base.update(overrides)
    return BatterGridLine(**base)  # type: ignore[arg-type]


def test_grid_line_cells_render_rates_and_named_absences() -> None:
    """D-079/D-081: a present line renders every column in its display
    shape; a scope missing at every reach states 'no data available', and a
    rate with no denominator is a styled dash — never an invented zero."""
    import streamlit_app

    texts, styles = streamlit_app._grid_line_cells(None)
    assert texts["AB"] == "no data available"
    assert set(texts) == {
        "AB",
        "H",
        "Barrels",
        "HR",
        "EV",
        "Barrel/PA %",
        "Hard-Hit %",
        "AVG",
        "SLG",
        "ISO",
        "+350 ft",
        "Pull Air %",
        "Oppo Air %",
        "xwOBA",
        "Swing-Str %",
    }
    assert set(styles) == set(texts)

    texts, styles = streamlit_app._grid_line_cells(_grid_line())
    assert texts["AB"] == "5"
    assert texts["EV"] == "95.5"
    assert texts["AVG"] == ".400"
    # D-097: a count of 350+ ft balls, not a rate.
    assert texts["+350 ft"] == "1"
    assert texts["Pull Air %"] == "40.0%"
    assert texts["Oppo Air %"] == "25.0%"
    assert texts["xwOBA"] == ".450"
    assert styles == {}

    texts, styles = streamlit_app._grid_line_cells(
        _grid_line(distance_350_count=None, pull_air_share=None, oppo_air_share=None)
    )
    assert texts["+350 ft"] == "—"
    assert texts["Pull Air %"] == "—"
    assert texts["Oppo Air %"] == "—"
    assert styles["+350 ft"] == streamlit_app._REASON_CSS
    assert styles["Pull Air %"] == streamlit_app._REASON_CSS


def test_grid_line_cells_add_the_gaps_on_the_season_view_only() -> None:
    """D-110: the season view alone carries xISO-ISO and xwOBA-wOBA, each
    signed with its PA sample, placed beside its sibling column, and
    reason-styled when the expected-stats board has no row for him."""
    import streamlit_app

    from greenmachine.live.pipeline import RegressionGaps

    gaps = RegressionGaps(
        xiso_minus_iso=Decimal("0.041"),
        xwoba_minus_woba=Decimal("-0.012"),
        plate_appearances=412,
    )
    texts, styles = streamlit_app._grid_line_cells(_grid_line(gaps=gaps), include_gaps=True)
    columns = list(texts)
    assert columns.index("xISO-ISO") == columns.index("ISO") + 1
    assert columns.index("xwOBA-wOBA") == columns.index("xwOBA") + 1
    assert texts["xISO-ISO"] == "+.041 (412 PA)"
    assert texts["xwOBA-wOBA"] == "-.012 (412 PA)"
    assert "xISO-ISO" not in styles  # a value cell carries no reason style
    # The L30 view (the default) never shows the columns, even with data.
    texts, _ = streamlit_app._grid_line_cells(_grid_line(gaps=gaps))
    assert "xISO-ISO" not in texts
    assert "xwOBA-wOBA" not in texts
    # No board row: the season view names the absence on both columns.
    texts, styles = streamlit_app._grid_line_cells(_grid_line(), include_gaps=True)
    assert texts["xISO-ISO"] == "—"
    assert texts["xwOBA-wOBA"] == "—"
    assert styles["xISO-ISO"] == streamlit_app._REASON_CSS
    assert styles["xwOBA-wOBA"] == streamlit_app._REASON_CSS
    # A scope missing at every reach still reads 'no data available' and
    # still gains the two gap columns as styled dashes.
    texts, styles = streamlit_app._grid_line_cells(None, include_gaps=True)
    assert texts["AB"] == "no data available"
    assert texts["xISO-ISO"] == "—"
    assert styles["xISO-ISO"] == streamlit_app._REASON_CSS
    assert styles["Oppo Air %"] == streamlit_app._REASON_CSS


def _board_with_grid_lines() -> SlateBoard:
    """The graded outage board with populated L30 and season grid lines, so
    the matchups grid and its season toggle have real figures to show."""
    import dataclasses as _dc

    from greenmachine.live.pipeline import BatterCard as _BatterCard

    board = _graded_board()
    l30 = _grid_line()
    season = _grid_line(
        pitches=900,
        plate_appearances=500,
        at_bats=440,
        hits=121,
        home_runs=33,
        exit_velocity=Decimal("91.5"),
        distance_350_count=None,
        pull_air_share=None,
    )

    def attach(cards: tuple[_BatterCard, ...]) -> tuple[_BatterCard, ...]:
        return tuple(
            _dc.replace(card, mix_line=l30, season_line=season, mix_label="last 30 days")
            for card in cards
        )

    game = board.games[0]
    regraded = _dc.replace(
        game,
        home_batters=attach(game.home_batters),
        away_batters=attach(game.away_batters),
    )
    return _dc.replace(board, games=(regraded, *board.games[1:]))


def test_matchups_grid_has_the_d079_columns_and_a_named_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-079: the grid is one row per batter with the ratified columns; the
    caption names the mix window actually used (D-025/D-081); the season
    toggle swaps the metric scope while the grade stays the L30 one."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_board", lambda **kwargs: _board_with_grid_lines())
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    st.cache_data.clear()
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    def grid_frames() -> list[pd.DataFrame]:
        frames = []
        for element in at.dataframe:
            frame = _display_values(element).astype(str)
            if "+350 ft" in frame.columns:
                frames.append(frame)
        return frames

    grids = grid_frames()
    assert grids, "the matchups grids rendered"
    # D-096/D-097/D-098: no BIP, no Form column; +350 ft is a count.
    expected = {
        "AB",
        "H",
        "Barrels",
        "HR",
        "EV",
        "Barrel/PA %",
        "Hard-Hit %",
        "AVG",
        "SLG",
        "ISO",
        "+350 ft",
        "Pull Air %",
        "xwOBA",
        "Swing-Str %",
        "Grade",
    }
    assert expected <= set(grids[0].columns)
    assert "BIP" not in grids[0].columns
    assert "Form (EV)" not in grids[0].columns
    assert set(grids[0]["AB"]) == {"5"}  # the L30 scope
    away_grades = grids[0]["Grade"].tolist()
    captions = " ".join(element.value for element in at.caption)
    assert "last 30 days" in captions
    assert "14%" in captions

    toggles = [toggle for toggle in at.toggle if toggle.key == "matchups_season_view"]
    assert toggles, "the season-view toggle rendered"
    toggles[0].set_value(True)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    grids = grid_frames()
    assert set(grids[0]["AB"]) == {"440"}  # the season scope
    assert set(grids[0]["+350 ft"]) == {"—"}  # no season source (D-081/D-090)
    assert set(grids[0]["Pull Air %"]) == {"—"}
    assert grids[0]["Grade"].tolist() == away_grades  # the grade stays L30


def test_slate_nav_regrades_the_chosen_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-101: the calendar date picker chooses the slate date the board
    builds — nothing else about the grading changes. Today, yesterday and
    tomorrow carry their relative word; any other date stands alone."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline

    seen: list[str] = []

    def fake_build(**kwargs: object) -> SlateBoard:
        seen.append(kwargs["slate_date"].isoformat())  # type: ignore[attr-defined]
        return _board_with_grid_lines()

    monkeypatch.setattr(pipeline, "build_board", fake_build)
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    st.cache_data.clear()
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    today = date.today()
    assert seen == [today.isoformat()]
    assert any("today" in h.value for h in at.subheader)

    nav = [c for c in at.date_input if c.key == "slate_date_choice"]
    assert nav, "the slate-date picker rendered"
    nav[0].set_value(today - timedelta(days=1))
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    yesterday = (today - timedelta(days=1)).isoformat()
    assert yesterday in seen
    assert any(yesterday in h.value and "yesterday" in h.value for h in at.subheader)

    nav = [c for c in at.date_input if c.key == "slate_date_choice"]
    nav[0].set_value(today + timedelta(days=1))
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    tomorrow = (today + timedelta(days=1)).isoformat()
    assert tomorrow in seen
    assert any(tomorrow in h.value and "tomorrow" in h.value for h in at.subheader)

    nav = [c for c in at.date_input if c.key == "slate_date_choice"]
    nav[0].set_value(today + timedelta(days=4))
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    later = (today + timedelta(days=4)).isoformat()
    assert later in seen
    heading = [h.value for h in at.subheader if later in h.value]
    assert heading and all("(today" not in h for h in heading)


def test_backtest_button_swaps_the_view(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-095: the top-right button opens the backtest view — pooled tallies
    per grade over past regraded slates — and the board button returns."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_board", lambda **kwargs: _board_with_grid_lines())
    # AppTest re-executes the script fresh, so same-module stubs do not
    # reach it; cut the network at the adapter method instead. Every
    # backtested day regrades to the staged board (official_date 2026-08-20),
    # and the stub's homer belongs to batter 101 — the staged S (home) and
    # B (away) cards. Outcomes read the game log (D-100).
    log = {
        BATTER_ID: (
            GameLogEntry(date="2026-08-20", game_pk=777001, home_runs=1, plate_appearances=4),
        )
    }
    monkeypatch.setattr(
        MlbStatsApi, "fetch_recent_game_logs", lambda self, ids, start, end: dict(log)
    )
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    st.cache_data.clear()
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert not any("Backtest — grade hit rates" in h.value for h in at.subheader)

    openers = [b for b in at.button if b.key == "view_backtest"]
    assert openers, "the backtest button rendered in the header"
    openers[0].click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any("Backtest — grade hit rates" in h.value for h in at.subheader)
    captions = " ".join(element.value for element in at.caption)
    assert "prior evening" in captions  # the no-leak method is named
    assert "no odds source" in captions  # ROI arithmetic is the viewer's own

    # Plain (unstyled) frames expose their DataFrame directly.
    frames = [element.value.astype(str) for element in at.dataframe]
    summary = [frame for frame in frames if "Hit rate" in frame.columns]
    assert summary, "the per-grade summary rendered"
    assert summary[0]["Grade"].tolist() == ["S", "A", "B", "C", "D"]
    # Seven regraded days, one staged batter per S/A/B/D each day; the stub
    # homer belongs to the S and B cards.
    assert summary[0]["Batters"].tolist() == ["7", "7", "7", "0", "7"]
    assert summary[0]["Homered"].tolist() == ["7", "0", "7", "0", "0"]
    assert summary[0]["Hit rate"].tolist()[0] == "100.0%"
    assert summary[0].loc[summary[0]["Grade"] == "C", "Hit rate"].iloc[0] == ("no batters graded")
    # +90.9% at the default -110 (0.9091 profit on a sure thing); -100% at 0%.
    assert summary[0].loc[summary[0]["Grade"] == "S", "ROI / 1u"].iloc[0] == "+90.9%"
    assert summary[0].loc[summary[0]["Grade"] == "A", "ROI / 1u"].iloc[0] == "-100.0%"

    closers = [b for b in at.button if b.key == "view_board"]
    assert closers, "the board button rendered while the backtest shows"
    closers[0].click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert not any("Backtest — grade hit rates" in h.value for h in at.subheader)


def test_backtest_excludes_a_day_the_source_has_not_indexed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-095: an empty outcome record on a day with games is a named
    exclusion — never tallied as a row of invented zero homers."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_board", lambda **kwargs: _board_with_grid_lines())
    monkeypatch.setattr(MlbStatsApi, "fetch_recent_game_logs", lambda self, ids, start, end: {})
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    st.cache_data.clear()
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    at.button(key="view_backtest").click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    captions = " ".join(element.value for element in at.caption)
    assert "Days not tallied" in captions
    assert "not tallied" in captions
    frames = [element.value.astype(str) for element in at.dataframe]
    summary = [frame for frame in frames if "Hit rate" in frame.columns]
    assert summary, "the per-grade summary still renders"
    assert summary[0]["Batters"].tolist() == ["0", "0", "0", "0", "0"]


def test_breakup_batter_half_carries_contact_shape_with_the_pitch_type_floor() -> None:
    """D-109: the batter half's EV and Air% read the window line — below
    the ratified 10-BBE pitch-type floor the value keeps its exact sample
    with an INSUFFICIENT marker; an empty denominator dashes."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(season_lines=(_season_line(),))
    markup = streamlit_app._arsenal_breakup_html(
        pitcher,
        (
            _pitch_line(
                batted_balls=7,
                mean_launch_speed=Decimal("91.23"),
                air_ball_share=Decimal("0.5"),
            ),
        ),
        threshold=0.15,
        side_filter=None,
        side_usage=None,
        window_label="last month",
        throws_text="right",
    )
    assert ">EV</th>" in markup
    assert ">Air%</th>" in markup
    assert "91.2 · n=7 · INSUFFICIENT" in markup
    assert "50.0% · n=7 · INSUFFICIENT" in markup
    # A full sample shows the plain values, no marker.
    markup_full = streamlit_app._arsenal_breakup_html(
        pitcher,
        (
            _pitch_line(
                batted_balls=12,
                mean_launch_speed=Decimal("91.23"),
                air_ball_share=Decimal("0.5"),
            ),
        ),
        threshold=0.15,
        side_filter=None,
        side_usage=None,
        window_label="last month",
        throws_text="right",
    )
    assert ">91.2</td>" in markup_full
    assert ">50.0%</td>" in markup_full
    assert "INSUFFICIENT" not in markup_full
    # No classified contact at all: dashes, never an invented zero.
    markup_empty = streamlit_app._arsenal_breakup_html(
        pitcher,
        (_pitch_line(batted_balls=0, mean_launch_speed=None, air_ball_share=None),),
        threshold=0.15,
        side_filter=None,
        side_usage=None,
        window_label="last month",
        throws_text="right",
    )
    row = markup_empty.split("4-Seam Fastball", 1)[1].split("</tr>", 1)[0]
    assert row.count("<td>—</td>") >= 2


def test_card_tags_carry_the_slot_and_the_high_k_reads() -> None:
    """D-109: the tags box gains the ordinal lineup slot (est.-marked),
    the high-K profile tag at the ratified 27% line, and the interaction
    tag when the opposing arm is also low-whiff — never both K tags."""
    from types import SimpleNamespace

    import streamlit_app

    result = SimpleNamespace(present_observations=[], missing_observations=[])
    card = SimpleNamespace(
        result=result,
        order_position=1,
        lineup_is_estimate=True,
        season_k_share=Decimal("0.28"),
        season=SimpleNamespace(plate_appearances=402),
        season_gaps=None,
        squared_up_share=None,
        squared_up_swings=0,
        squared_up_bat_speed=None,
    )
    arm = SimpleNamespace(season_whiff_weighted=Decimal("0.20"))
    tags = streamlit_app._card_tags(card, arm)
    assert "est. lineup" in tags
    assert "bats 1st (est.)" in tags
    assert "high-K bat vs low-whiff arm: K% 28.0 (402 PA), arsenal whiff 20.0%" in tags
    assert "high-K profile" not in tags  # the interaction tag supersedes it
    # A normal-whiff arm leaves the descriptive profile tag.
    tags = streamlit_app._card_tags(card, SimpleNamespace(season_whiff_weighted=Decimal("0.25")))
    assert "high-K profile: K% 28.0 (402 PA)" in tags
    # Below the ratified line, and no line at all: no K tag.
    quiet = SimpleNamespace(**{**vars(card), "season_k_share": Decimal("0.20")})
    assert "high-K" not in streamlit_app._card_tags(quiet, arm)
    no_line = SimpleNamespace(**{**vars(card), "season_k_share": None, "season": None})
    assert "high-K" not in streamlit_app._card_tags(no_line, arm)


def test_card_tags_carry_the_x_gap_and_contact_first_reads() -> None:
    """D-110: the x-gap tag fires when EITHER season gap's absolute value
    reaches .030 — both values always shown with the PA sample; the
    contact-first tag needs squared-up ≥ 35% AND bat speed ≥ 72 mph."""
    from types import SimpleNamespace

    import streamlit_app

    from greenmachine.live.pipeline import RegressionGaps

    base = dict(
        result=SimpleNamespace(present_observations=[], missing_observations=[]),
        order_position=None,
        lineup_is_estimate=False,
        season_k_share=None,
        season=None,
        season_gaps=None,
        squared_up_share=None,
        squared_up_swings=0,
        squared_up_bat_speed=None,
    )
    # Either gap trips the tag; the other value still prints.
    over = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("0.041"),
                xwoba_minus_woba=Decimal("-0.012"),
                plate_appearances=412,
            ),
        }
    )
    tags = streamlit_app._card_tags(over, None)
    assert "x-gap: xISO +.041, xwOBA -.012 (season, 412 PA)" in tags
    flipped = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("0.010"),
                xwoba_minus_woba=Decimal("0.030"),
                plate_appearances=88,
            ),
        }
    )
    assert "x-gap" in streamlit_app._card_tags(flipped, None)
    # Under the line on both, and no board row: no tag.
    under = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("0.029"),
                xwoba_minus_woba=Decimal("-0.029"),
                plate_appearances=88,
            ),
        }
    )
    assert "x-gap" not in streamlit_app._card_tags(under, None)
    assert "x-gap" not in streamlit_app._card_tags(SimpleNamespace(**base), None)
    # Contact-first: both sides of the ratified line are required.
    contact = SimpleNamespace(
        **{
            **base,
            "squared_up_share": Decimal("0.362"),
            "squared_up_swings": 620,
            "squared_up_bat_speed": Decimal("73.4"),
        }
    )
    tags = streamlit_app._card_tags(contact, None)
    assert "contact-first profile: squared-up 36.2% (620 swings), bat speed 73.4 mph" in tags
    slow_bat = SimpleNamespace(**{**vars(contact), "squared_up_bat_speed": Decimal("71.9")})
    assert "contact-first" not in streamlit_app._card_tags(slow_bat, None)
    low_squared = SimpleNamespace(**{**vars(contact), "squared_up_share": Decimal("0.349")})
    assert "contact-first" not in streamlit_app._card_tags(low_squared, None)


def test_ordinal_never_says_1th() -> None:
    import streamlit_app

    assert streamlit_app._ordinal(1) == "1st"
    assert streamlit_app._ordinal(2) == "2nd"
    assert streamlit_app._ordinal(3) == "3rd"
    assert streamlit_app._ordinal(4) == "4th"
    assert streamlit_app._ordinal(9) == "9th"
    assert streamlit_app._ordinal(11) == "11th"
    assert streamlit_app._ordinal(13) == "13th"


def test_breakup_builder_escapes_pitch_names() -> None:
    """D-106: the table renders through raw HTML, so a pitch name carrying
    markup characters arrives escaped — a data string never becomes page
    structure."""
    from types import SimpleNamespace

    import streamlit_app

    pitcher = SimpleNamespace(
        season_lines=(_season_line(pitch_name="<b>Fastball</b>"),),
    )
    markup = streamlit_app._arsenal_breakup_html(
        pitcher,
        (),
        threshold=0.15,
        side_filter=None,
        side_usage=None,
        window_label="last month",
        throws_text=None,
    )
    assert "<b>Fastball</b>" not in markup
    assert "&lt;b&gt;Fastball&lt;/b&gt;" in markup
    # No throwing side on the board: the header names the generic scope
    # (html.escape quotes the apostrophe — the header text is escaped too).
    assert "vs the starter&#x27;s side" in markup
