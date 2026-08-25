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

import dataclasses
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

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
from greenmachine.live.pipeline import (
    PitcherRecentLine,
    PitcherSeasonReads,
    SlateBoard,
    build_board,
)
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

    def fetch_recent_pitching_logs(
        self, player_ids: tuple[int, ...], start_mmddyyyy: str, end_mmddyyyy: str
    ) -> FetchFailure:
        return FetchFailure("pitching-game-logs: simulated outage")


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
                avg_launch_angle=Decimal("16.4"),
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

    def fetch_pitcher_expected_stats(self, *, year: int) -> dict:
        return {}

    def fetch_statcast_pitchers(self, *, year: int, minimum: int = 0) -> dict:
        return {}

    def fetch_batted_ball(self, *, year: int, minimum: int = 0) -> dict:
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
    # Arms and conditions dataframes at minimum — the shortlist renders as
    # bubble rows, not a data grid (D-126).
    assert len(at.dataframe) >= 2


def test_sluggers_render_as_bubble_rows_with_more_buttons(_staged_app: SlateBoard) -> None:
    """D-126 (PO): the shortlist renders as bubble rows — no dataframe, no
    For-HR or Against-HR columns anywhere — with hoverable pills, header
    definitions on hover, and a More button per row that opens the batter
    detail."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    tab = at.tabs[0]
    assert len(list(tab.dataframe)) == 0
    markup = "\n".join(element.value for element in tab.markdown)
    assert "gm-pill" in markup
    assert 'class="gm-head"' in markup
    buttons = [button for button in tab.button if button.label == "More"]
    assert len(buttons) == 2  # the two A/S batters on the staged board
    buttons[0].click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    # The batter detail opened: its recent-form caption names the batter.
    opened = "\n".join(element.value for element in at.markdown)
    assert "Batter detail" in opened or "recent form" in opened.lower()


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
    shortlist those reasons ride the note bubbles (D-126)."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    for element in at.dataframe:
        display = _display_values(element).astype(str)
        assert not display.isin(["None", "nan"]).any().any()
    # The shortlist batters' note bubbles name the absences in words.
    markup = "\n".join(element.value for element in at.tabs[0].markdown).lower()
    assert "missing:" in markup
    assert "source unavailable" in markup


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
    # D-128 (PO): the only radios on the board are the Matchups tab's
    # batter-window selector — scope picks, never a ranking control.
    assert {radio.key for radio in at.radio} <= {
        "matchups_view_mode",
        "matchups_window_unit",
    }
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


def test_shortlist_keeps_only_a_and_s_as_bubble_rows() -> None:
    """D-084/D-126 (PO): the Sluggers tab is the shortlist — grades A and S
    only, rendered as bubble rows in the PO's column order (identity, the
    tag bubbles, the conditions, the parked reads, grade last, then the
    More button). The For-HR and Against-HR columns are gone; their reads
    live on as green and red pills."""
    import streamlit_app

    rows = streamlit_app._slugger_rows(_graded_board())
    assert streamlit_app._SLUGGER_HEADERS == (
        "Batter",
        "HR",
        "Team",
        "Versus",
        "Tags",
        "Weather",
        "Park factor",
        "Form Score",
        "Grade",
        "",
    )
    assert [row.card.result.grade.value for row in rows] == ["S", "A"]
    # D-094: the outage board fetched no events, so no batter has a last
    # game day at all and the money tag stays blank — never a guess.
    assert [row.money_day for row in rows] == [None, None]
    # The outage venue is roofed: the weather cell says so, in words.
    assert [row.weather for row in rows] == ["roofed — indoor neutral value"] * 2
    assert not any(row.weather_absent for row in rows)
    # Park factor formatted as the whole-number factor for the batting side.
    assert all(row.factor_text in {"112", "98", "not covered"} for row in rows)
    # Pills are (label, kind, explanation) triples — the full read rides
    # the hover, the For/Against/note order keeps the D-114 reading order.
    for row in rows:
        for label, kind, explanation in row.pills:
            assert kind in {"for", "against", "note"}
            assert label and explanation


def test_money_tag_marks_a_batter_who_homered_with_the_date() -> None:
    """D-094/D-126 (PO): the neon tag carries the homer's game date —
    "$8/23" — so a pre-game read never passes last night's homer off as
    tonight's; a batter without one stays blank."""
    import dataclasses

    import streamlit_app

    board = _graded_board()
    game = board.games[0]
    tagged = dataclasses.replace(game.home_batters[0], homered_on_last_game_day="2026-08-23")
    game = dataclasses.replace(game, home_batters=(tagged, *game.home_batters[1:]))
    board = dataclasses.replace(board, games=(game, *board.games[1:]))
    rows = streamlit_app._slugger_rows(board)
    assert rows[0].money_day == "8/23"
    assert rows[0].money_iso == "2026-08-23"
    assert rows[1].money_day is None


def test_shortlist_empty_when_nothing_grades_a_or_s() -> None:
    """All-D slate: the shortlist is empty and the tab says so plainly."""
    import streamlit_app

    assert streamlit_app._slugger_rows(_outage_board()) == []


def test_pill_labels_take_the_tags_own_name() -> None:
    """D-126: a bubble's face is the tag's own name before the colon; a
    short colon-less tag is its own face; a long one truncates, and the
    full read always rides the hover."""
    import streamlit_app

    assert streamlit_app._pill_label("x-gap: xISO +.006 (season, 564 PA)") == "x-gap"
    assert streamlit_app._pill_label("power profile: EV 93.0 mph") == "power profile"
    assert streamlit_app._pill_label("barrel 16.1% (320 BBE)") == "barrel 16.1% (320 BBE)"
    assert streamlit_app._pill_label("bats 3rd") == "bats 3rd"
    assert streamlit_app._pill_label("x" * 40).endswith("...")
    pills = streamlit_app._tag_pills(
        ["low sample: pull pct air balls"],
        ["power profile: EV 93.0 mph, bat speed 79.7 mph (season)"],
        ["high-K profile: K% 31.0 (402 PA)"],
    )
    assert [kind for _, kind, _ in pills] == ["for", "against", "note"]
    assert pills[0][0] == "power profile"
    assert pills[0][2] == "power profile: EV 93.0 mph, bat speed 79.7 mph (season)"
    # The markup escapes the hover text and names the kind's class.
    markup = streamlit_app._pills_html(pills)
    assert 'class="gm-pill gm-pill-for"' in markup
    assert 'title="power profile: EV 93.0 mph, bat speed 79.7 mph (season)"' in markup


def test_conditions_text_speaks_field_words() -> None:
    """D-126 (PO): the shortlist weather pairs the start-time temperature
    with the wind in field words off the measured axis — "84°F · 12 mph
    out to right" — the compass reading as the honest fallback, a roof as
    the indoor neutral value, nothing sourced as the plain reason."""
    import dataclasses
    from decimal import Decimal

    import streamlit_app

    from greenmachine.inputs.contract import VenueType

    board = _graded_board()
    game = board.games[0]
    assert streamlit_app._conditions_text(game) == ("roofed — indoor neutral value", False)
    open_air = dataclasses.replace(
        game,
        venue_type=VenueType.OPEN_AIR,
        temperature_fahrenheit=Decimal("84"),
        wind_speed_mph=Decimal("12"),
        wind_from_degrees=Decimal("315"),
        park_orientation_degrees=Decimal("90"),
        wind_direction="NW",
    )
    assert streamlit_app._conditions_text(open_air) == ("84°F · 12 mph out to right", False)
    no_axis = dataclasses.replace(open_air, park_orientation_degrees=None)
    assert streamlit_app._conditions_text(no_axis) == ("84°F · 12 mph NW", False)
    empty = dataclasses.replace(
        open_air,
        temperature_fahrenheit=None,
        wind_speed_mph=None,
        wind_from_degrees=None,
        wind_direction=None,
    )
    assert streamlit_app._conditions_text(empty) == ("source unavailable", True)


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


def _pitcher_breakup_line(**overrides: object) -> object:
    """The pitcher half's season line (D-129): event-computed off his season
    pitch record — the counting and expected fields the arsenal board never
    published (the raw barrel count, the per-side xISO)."""
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
        "home_runs": 12,
        "barrel_share": Decimal("0.09"),
        "hard_hit_share": Decimal("0.40"),
        "expected_woba": Decimal("0.335"),
        "whiff_share": Decimal("0.24"),
        "woba": Decimal("0.310"),
        "strikeout_share": Decimal("0.22"),
        "batted_balls": 75,
        "at_bats": 92,
        "hits": 23,
        "barrel_count": 7,
        "expected_iso": Decimal("0.165"),
    }
    base.update(overrides)
    return PitchLine(**base)  # type: ignore[arg-type]


def _batter_breakup_line(**overrides: object) -> object:
    """The batter half's season line against the pitch (D-129): AB and Hits
    in, PA out; LA right after Hits, then barrel rate and EV; the pull/oppo
    air reads over the form section's measurable-air convention."""
    from greenmachine.live.pipeline import PitchLine

    base = {
        "pitch_type": "FF",
        "pitch_name": "4-Seam Fastball",
        "pitches": 120,
        "usage_share": Decimal("0.40"),
        "plate_appearances": 32,
        "batting_average": Decimal("0.280"),
        "slugging": Decimal("0.520"),
        "iso": Decimal("0.240"),
        "home_runs": 2,
        "barrel_share": Decimal("0.12"),
        "hard_hit_share": Decimal("0.45"),
        "expected_woba": Decimal("0.355"),
        "whiff_share": Decimal("0.26"),
        "batted_balls": 25,
        "mean_launch_speed": Decimal("93.2"),
        "air_ball_share": Decimal("0.52"),
        "mean_launch_angle": Decimal("21.5"),
        "at_bats": 50,
        "hits": 14,
        "barrel_count": 3,
        "pull_air_share": Decimal("0.44"),
        "oppo_air_share": Decimal("0.15"),
    }
    base.update(overrides)
    return PitchLine(**base)  # type: ignore[arg-type]


def test_breakup_table_pairs_the_two_season_halves() -> None:
    """The D-129 table: pitcher season scope on the left, batter season scope
    on the right, usage above the threshold, ISO only on the batter half."""
    import streamlit_app

    markup = streamlit_app._arsenal_breakup_html(
        (
            _pitcher_breakup_line(),
            _pitcher_breakup_line(
                pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.05")
            ),
        ),
        {"FF": _batter_breakup_line()},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )

    assert "Pitcher — season vs LHB" in markup
    assert "Batter — season vs RHP" in markup
    assert ">45.0%<" in markup
    assert "<td>100</td>" in markup
    assert ">.165<" in markup
    assert ">.310<" in markup
    assert ">.335<" in markup
    assert ">22.0%<" in markup
    assert "<td>7</td>" in markup
    pitcher_half = markup.split("gm-half-boundary")[0]
    assert ">ISO</th>" not in pitcher_half
    assert 'class="gm-half-boundary">50</td>' in markup
    assert "<td>14</td>" in markup
    assert ">21.5°<" in markup
    assert ">12.0%<" in markup
    assert ">93.2<" in markup
    assert ">44.0%<" in markup
    assert ">15.0%<" in markup
    assert "Changeup" not in markup
    assert "gm-dim" not in markup


def test_breakup_table_dashes_a_pitch_the_batter_has_not_seen() -> None:
    """A pitch the batter never faced shows AB 0 and dashes for the rest of
    his half — the absence is explicit, never invented."""
    import streamlit_app

    markup = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )

    assert '<td class="gm-half-boundary">0</td>' in markup
    assert markup.count("<td>—</td>") == 14


def test_breakup_threshold_hides_rows_and_can_empty_the_table() -> None:
    """Below-threshold rows hide outright (D-129 item 10); a threshold above
    every usage empties the table so the dialog can caption the state."""
    import streamlit_app

    lines = (
        _pitcher_breakup_line(),
        _pitcher_breakup_line(pitch_type="CH", pitch_name="Changeup", usage_share=Decimal("0.10")),
    )
    markup = streamlit_app._arsenal_breakup_html(
        lines,
        {"FF": _batter_breakup_line()},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert "4-Seam Fastball" in markup
    assert "Changeup" not in markup

    empty = streamlit_app._arsenal_breakup_html(
        lines,
        {"FF": _batter_breakup_line()},
        threshold=0.50,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert empty == ""


def test_breakup_row_verdict_colors_need_both_halves_and_real_samples() -> None:
    """The D-129 row verdict: pitcher green band + batter green band paints
    the row green, both red paints it red, and thin samples stay neutral."""
    import streamlit_app

    good = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {"FF": _batter_breakup_line()},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert 'tr class="gm-row-good"' in good

    bad = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(expected_woba=Decimal("0.260")),),
        {"FF": _batter_breakup_line(slugging=Decimal("0.300"))},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert 'tr class="gm-row-bad"' in bad

    mixed = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {"FF": _batter_breakup_line(slugging=Decimal("0.400"))},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert "gm-row-good" not in mixed
    assert "gm-row-bad" not in mixed

    thin_pitcher = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(batted_balls=7),),
        {"FF": _batter_breakup_line()},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert "gm-row-good" not in thin_pitcher

    thin_batter = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {"FF": _batter_breakup_line(batted_balls=5)},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert "gm-row-good" not in thin_batter

    unseen = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {},
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert "gm-row-good" not in unseen
    assert "gm-row-bad" not in unseen


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
        "robbed_hr_count": 1,
        "pull_air_share": Decimal("0.4"),
        "straight_air_share": Decimal("0.3"),
        "oppo_air_share": Decimal("0.25"),
        "expected_woba": Decimal("0.45"),
        "whiff_share": Decimal("0.12"),
    }
    base.update(overrides)
    return BatterGridLine(**base)  # type: ignore[arg-type]


def test_grid_line_cells_render_rates_and_named_absences() -> None:
    """D-079/D-081: a present line renders every column in its display
    shape; a scope missing at every reach states 'no data available', and a
    rate with no denominator is a styled dash — never an invented zero.
    D-124: the recent view stars the two signed spray shares, whose metrics
    carry ratified v2.2 firing lines. D-128 (PO): the third air profile —
    Straight Air % — grids unstarred between them."""
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
        "Robbed HR",
        "Pull Air % ★",
        "Straight Air %",
        "Oppo Air % ★",
        "xwOBA",
        "Swing-Str %",
    }
    assert set(styles) == set(texts)

    texts, styles = streamlit_app._grid_line_cells(_grid_line())
    assert texts["AB"] == "5"
    assert texts["EV"] == "95.5"
    assert texts["AVG"] == ".400"
    # PO 2026-08-24: robbed HRs — 375+ ft balls that stayed in the park,
    # last 7 days — a raw count, not a rate.
    assert texts["Robbed HR"] == "1"
    assert texts["Pull Air % ★"] == "40.0%"
    assert texts["Straight Air %"] == "30.0%"
    assert texts["Oppo Air % ★"] == "25.0%"
    assert texts["xwOBA"] == ".450"
    # D-127 (PO): the researched bands grade every valued rate cell —
    # three greens to dark at elite, three reds to dark at very poor. The
    # counting columns and the Straight/Oppo Air % fit reads stay neutral.
    assert styles == {
        "EV": streamlit_app._BAND_G3_CSS,  # 95.5 ≥ 91
        "Barrel/PA %": streamlit_app._BAND_G3_CSS,  # 16.7% ≥ 9%
        "Hard-Hit %": streamlit_app._BAND_G2_CSS,  # 50% ≥ 46%
        "AVG": streamlit_app._BAND_G3_CSS,  # .400 ≥ .285
        "SLG": streamlit_app._BAND_G3_CSS,  # 1.000 ≥ .500
        "ISO": streamlit_app._BAND_G3_CSS,  # .600 ≥ .240
        "Pull Air % ★": streamlit_app._BAND_G2_CSS,  # 40% ≥ 38%
        "xwOBA": streamlit_app._BAND_G3_CSS,  # .450 ≥ .370
        "Swing-Str %": streamlit_app._BAND_G3_CSS,  # 12% ≤ 18%
    }
    assert "Straight Air %" not in styles
    assert "Oppo Air % ★" not in styles

    texts, styles = streamlit_app._grid_line_cells(
        _grid_line(
            robbed_hr_count=None,
            pull_air_share=None,
            straight_air_share=None,
            oppo_air_share=None,
        )
    )
    assert texts["Robbed HR"] == "—"
    assert texts["Pull Air % ★"] == "—"
    assert texts["Straight Air %"] == "—"
    assert texts["Oppo Air % ★"] == "—"
    assert styles["Robbed HR"] == streamlit_app._REASON_CSS
    assert styles["Pull Air % ★"] == streamlit_app._REASON_CSS
    assert styles["Straight Air %"] == streamlit_app._REASON_CSS


def _sp_reads() -> PitcherSeasonReads:
    return PitcherSeasonReads(
        plate_appearances=620,
        woba=Decimal("0.320"),
        expected_woba=Decimal("0.297"),
        iso=Decimal("0.170"),
        expected_iso=Decimal("0.180"),
        batted_ball_events=450,
        barrel_share=Decimal("0.08"),
        avg_launch_angle=Decimal("12.9"),
        hard_hit_share=Decimal("0.42"),
        home_runs=26,
        home_run_per_nine=Decimal("1.50"),
        innings_text="150.1",
    )


def test_sp_season_row_marks_the_digest_reads_green() -> None:
    """D-111: green marks only the digest's pitcher-vulnerability read —
    HR/9 at or above the ratified line — and the samples ride the Scope
    label beside the rates they basis. D-128 (PO): wOBA and ISO left the
    pitcher tables — xwOBA and xISO stay — Hard-Hit % joined, and the
    wOBA-over-xwOBA highlight went with its column."""
    import streamlit_app

    row, styles = streamlit_app._sp_season_row(_sp_reads())
    assert row["Scope"] == "Season — 620 PA · 450 BBE · 150.1 IP"
    assert "wOBA" not in row and "ISO" not in row
    assert row["xwOBA"] == ".297"
    assert row["HR"] == "26"
    assert row["HR/9"] == "1.50"
    assert row["BRL%"] == "8.0%"
    assert row["Hard-Hit %"] == "42.0%"
    assert row["LA"] == "12.9°"
    assert row["xISO"] == ".180"
    assert styles["HR/9"] == streamlit_app._HIGHLIGHT
    # D-127 (PO): the researched vulnerability bands grade the rest —
    # the "no invented bands" posture is superseded by the PO's
    # color-graded-cells directive, with every edge printed on the
    # surface (D-079). The ratified green read keeps precedence.
    assert styles["xwOBA"] == streamlit_app._BAND_R1_CSS  # .297 < .300
    assert styles["BRL%"] == streamlit_app._BAND_G1_CSS  # 8.0% ≥ 8%
    assert styles["Hard-Hit %"] == streamlit_app._BAND_G1_CSS  # 42% ≥ 40%
    assert styles["xISO"] == streamlit_app._BAND_G2_CSS  # .180 ≥ .170
    assert "LA" not in styles  # 12.9° — the neutral middle
    # On the line's other side: no ratified green — the researched bands
    # still grade what the cells are worth (HR/9 1.39 lands strong green
    # on the vulnerability scale).
    flipped = dataclasses.replace(_sp_reads(), home_run_per_nine=Decimal("1.39"))
    _, styles = streamlit_app._sp_season_row(flipped)
    assert styles["HR/9"] == streamlit_app._BAND_G2_CSS


def test_sp_season_row_names_absences_and_the_contact_floor() -> None:
    """D-111: no sources at all is a named absence row; a thin Statcast
    sample keeps its contact reads under the amber advisory, never hidden."""
    import streamlit_app

    row, styles = streamlit_app._sp_season_row(None)
    assert row["Scope"] == "Season — no season record"
    assert all(text == "—" for key, text in row.items() if key != "Scope")
    assert styles["xwOBA"] == streamlit_app._REASON_CSS
    thin = dataclasses.replace(_sp_reads(), batted_ball_events=12)
    row, styles = streamlit_app._sp_season_row(thin)
    assert row["Scope"].endswith("INSUFFICIENT")
    assert styles["BRL%"] == streamlit_app._INSUFFICIENT_CSS
    assert styles["Hard-Hit %"] == streamlit_app._INSUFFICIENT_CSS
    assert styles["LA"] == streamlit_app._INSUFFICIENT_CSS
    assert row["BRL%"] == "8.0%"  # the value stays visible (D-068)


def _sp_line() -> PitcherRecentLine:
    return PitcherRecentLine(
        plate_appearances=41,
        batted_balls=33,
        home_runs=3,
        woba=Decimal("0.355"),
        expected_woba=Decimal("0.310"),
        barrel_share=Decimal("0.12"),
        avg_launch_angle=Decimal("17.5"),
        air_ball_share=Decimal("0.55"),
        iso=Decimal("0.210"),
        hard_hit_share=Decimal("0.50"),
        ground_ball_share=Decimal("0.38"),
        classified_batted_balls=30,
    )


def test_sp_recent_row_names_the_two_month_absences() -> None:
    """D-111: the event scope publishes no innings and no per-event expected
    SLG, so HR/9 and xISO name their absences and the HR count shows.
    D-128 (PO): the scope is the last two months now, and wOBA left the
    pitcher tables."""
    import streamlit_app

    row, styles = streamlit_app._sp_recent_row("vs L (2M)", _sp_line(), vulnerability_floor=True)
    assert row["Scope"] == "vs L (2M) — 41 BF · 33 BBE · INSUFFICIENT"
    assert row["HR"] == "3"
    assert row["HR/9"] == "—"
    assert row["xISO"] == "—"
    assert "wOBA" not in row
    assert row["Hard-Hit %"] == "50.0%"
    assert styles["HR/9"] == streamlit_app._REASON_CSS
    assert styles["xISO"] == streamlit_app._REASON_CSS
    # Below the ratified vulnerability floor (80 BF / 40 BBE): amber, with
    # the values still visible.
    assert styles["xwOBA"] == streamlit_app._INSUFFICIENT_CSS
    assert row["xwOBA"] == ".310"
    # An empty scope names itself.
    row, styles = streamlit_app._sp_recent_row("vs R (2M)", None)
    assert row["Scope"] == "vs R (2M) — no recent record"
    assert styles["xwOBA"] == streamlit_app._REASON_CSS


def test_sp_recent_row_at_the_floor_carries_no_advisory() -> None:
    """D-111: exactly 80 BF and 40 BBE meets the floor — the amber is for
    below the line, never at it. The researched bands still grade."""
    import streamlit_app

    line = dataclasses.replace(_sp_line(), plate_appearances=80, batted_balls=40)
    row, styles = streamlit_app._sp_recent_row("vs R (2M)", line, vulnerability_floor=True)
    assert "INSUFFICIENT" not in row["Scope"]
    assert streamlit_app._INSUFFICIENT_CSS not in styles.values()
    # 50% hard-hit against is past the elite edge on the vulnerability scale.
    assert styles["Hard-Hit %"] == streamlit_app._BAND_G3_CSS


def test_workload_facts_one_wording_both_surfaces() -> None:
    """D-123 (SP-3): the Arms columns and the dialog echo share the one
    helper — raw facts, the ratified 100-pitch flag named, the absence in
    words, never a cap claim."""
    import streamlit_app

    from greenmachine.live.pipeline import StarterWorkload

    assert streamlit_app._workload_facts(None) == (
        "no start record in the lookback window",
        "—",
    )
    workload = StarterWorkload(
        last_start_date="2026-08-18",
        last_start_pitches=101,
        days_since_last_start=1,
        last_starts=(101, 88, 92),
        starts_in_window=3,
        workload_flag=True,
        thin_sample=False,
    )
    last, last_three = streamlit_app._workload_facts(workload)
    assert last == "101 pitches, 1 day ago · workload flag"
    assert last_three == "101/88/92 pitches"
    light = dataclasses.replace(
        workload, last_start_pitches=87, days_since_last_start=4, workload_flag=False
    )
    last, _ = streamlit_app._workload_facts(light)
    assert last == "87 pitches, 4 days ago"


def test_arms_carries_the_workload_columns_with_their_absence_named(
    _staged_app: SlateBoard,
) -> None:
    """D-123 (SP-3): the Arms tab carries the raw workload columns; on the
    outage board the cells name the absence, never a blank or a None."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    for element in at.dataframe:
        display = _display_values(element).astype(str)
        if "Last start" not in display.columns:
            continue
        last_start = display["Last start"].tolist()
        assert "no start record in the lookback window" in last_start
        assert "starter not announced" in last_start
        pair = display[["Last start", "Last 3 starts"]]
        assert not pair.isin(["None", "nan", ""]).any().any()
        return
    raise AssertionError("no dataframe carried the workload columns")


def test_arms_metrics_mirror_the_card_rules_on_both_scopes() -> None:
    """D-111: the Arms tab carries the card metrics plus the air mirror,
    with the samples as their own columns; the season scope names the air
    share absent (the board's fbld/gb columns are exit velocities, not a
    split), and the two-month scope names HR/9 and xISO absent exactly like
    the cards. D-128 (PO): wOBA and ISO left the pitcher tables — xwOBA
    and xISO stay — and Hard-Hit % joined both scopes."""
    import streamlit_app

    texts, styles = streamlit_app._arms_season_metrics(_sp_reads())
    assert texts["PA"] == "620"
    assert texts["BBE"] == "450"
    assert "wOBA" not in texts and "ISO" not in texts
    assert texts["xwOBA"] == ".297"
    assert texts["Hard-Hit %"] == "42.0%"
    # The season board publishes no air split — a named absence, recent only.
    assert texts["Air %"] == "—"
    assert styles["Air %"] == streamlit_app._REASON_CSS
    # D-116 (PO): GB% lives on the recent view only — the season scope does
    # not carry the column at all.
    assert "GB %" not in texts
    assert styles["HR/9"] == streamlit_app._HIGHLIGHT
    texts, styles = streamlit_app._arms_recent_metrics(_sp_line())
    assert texts["PA"] == "41"
    assert texts["BBE"] == "33"
    assert "wOBA" not in texts and "ISO" not in texts
    assert texts["xwOBA"] == ".310"
    assert texts["Hard-Hit %"] == "50.0%"
    assert texts["HR"] == "3"
    assert texts["HR/9"] == "—"
    assert texts["xISO"] == "—"
    assert texts["Air %"] == "55.0%"
    assert texts["GB %"] == "38.0%"
    # GB % reads its own denominator: below the 15-BBE floor on classified
    # contact it keeps its value under the amber advisory.
    thin = dataclasses.replace(_sp_line(), classified_batted_balls=12)
    texts, styles = streamlit_app._arms_recent_metrics(thin)
    assert texts["GB %"] == "38.0%"
    assert styles["GB %"] == streamlit_app._INSUFFICIENT_CSS
    # No record at all: a fully named absence, never invented zeros.
    texts, styles = streamlit_app._arms_recent_metrics(None)
    assert all(text == "—" for text in texts.values())
    assert styles["xwOBA"] == streamlit_app._REASON_CSS
    assert "GB %" in texts  # the recent column set carries it even on an empty scope


def test_grid_line_cells_carry_no_gap_columns_on_either_view() -> None:
    """D-125 (PO): the D-110 regression gaps left the grid for the
    Sluggers tags — neither view shows xISO-ISO or xwOBA-wOBA, while ISO
    and xwOBA themselves stay (PO: keep both). D-124: the season view
    stars the power-profile EV and carries the season average launch
    angle after EV — unstarred context, never a firing line."""
    import streamlit_app

    from greenmachine.live.pipeline import RegressionGaps

    gaps = RegressionGaps(
        xiso_minus_iso=Decimal("0.041"),
        xwoba_minus_woba=Decimal("-0.012"),
        plate_appearances=412,
    )
    texts, styles = streamlit_app._grid_line_cells(
        _grid_line(gaps=gaps, avg_launch_angle=Decimal("16.4")), include_gaps=True
    )
    columns = list(texts)
    assert columns.index("LA") == columns.index("EV ★") + 1
    assert texts["LA"] == "16.4°"
    # D-127: an average carries no firing line, but it still wears its
    # researched bucket — 16.4° lands the strong band (≥ 14.5).
    assert styles["LA"] == streamlit_app._BAND_G2_CSS
    assert "ISO" in texts and "xwOBA" in texts
    for gone in ("xISO-ISO", "xISO-ISO ★", "xwOBA-wOBA", "xwOBA-wOBA ★"):
        assert gone not in texts
    # The recent-window view never shows LA either.
    texts, _ = streamlit_app._grid_line_cells(
        _grid_line(gaps=gaps, avg_launch_angle=Decimal("16.4"))
    )
    assert "LA" not in texts
    # No board row: the season view names the LA absence.
    texts, styles = streamlit_app._grid_line_cells(_grid_line(), include_gaps=True)
    assert texts["LA"] == "—"
    assert styles["LA"] == streamlit_app._REASON_CSS
    # A scope missing at every reach still reads 'no data available'.
    texts, styles = streamlit_app._grid_line_cells(None, include_gaps=True)
    assert texts["AB"] == "no data available"
    assert styles["Oppo Air %"] == streamlit_app._REASON_CSS


def test_band_css_walks_all_six_bands_in_both_directions() -> None:
    """D-127 (PO): three greens to dark at elite, three reds to dark at
    very poor, the neutral middle unfilled — and a lower-is-better metric
    mirrors the walk."""
    import streamlit_app

    spec = streamlit_app._GRID_BANDS["EV"]  # 91/90/89 over 88/87/85.5
    assert streamlit_app._band_css(spec, 91.0) == streamlit_app._BAND_G3_CSS
    assert streamlit_app._band_css(spec, 90.4) == streamlit_app._BAND_G2_CSS
    assert streamlit_app._band_css(spec, 89.0) == streamlit_app._BAND_G1_CSS
    assert streamlit_app._band_css(spec, 88.4) is None  # the neutral middle
    assert streamlit_app._band_css(spec, 87.9) == streamlit_app._BAND_R1_CSS
    assert streamlit_app._band_css(spec, 86.0) == streamlit_app._BAND_R2_CSS
    assert streamlit_app._band_css(spec, 84.0) == streamlit_app._BAND_R3_CSS

    low = streamlit_app._GRID_BANDS["Swing-Str %"]  # 18/21/24 over 27/30/33
    assert streamlit_app._band_css(low, 0.17) == streamlit_app._BAND_G3_CSS
    assert streamlit_app._band_css(low, 0.255) is None
    assert streamlit_app._band_css(low, 0.34) == streamlit_app._BAND_R3_CSS
    # The extremes ARE the console's highlight/veto pair — one language.
    assert streamlit_app._BAND_G3_CSS == streamlit_app._HIGHLIGHT
    assert streamlit_app._BAND_R3_CSS == streamlit_app._VETO_CSS


def test_bands_never_outrank_an_absence_an_advisory_or_the_ratified_green() -> None:
    """D-127's precedence: a named absence, the amber INSUFFICIENT
    advisory and the ratified green all outrank a researched bucket."""
    import streamlit_app

    # A None rate keeps its styled dash, never a bucket.
    texts, styles = streamlit_app._grid_line_cells(_grid_line(exit_velocity=None))
    assert texts["EV"] == "—"
    assert styles["EV"] == streamlit_app._REASON_CSS
    # A thin contact sample keeps the amber advisory over the bucket.
    thin = dataclasses.replace(_sp_reads(), batted_ball_events=12)
    _, styles = streamlit_app._sp_season_row(thin)
    assert styles["BRL%"] == streamlit_app._INSUFFICIENT_CSS
    assert styles["LA"] == streamlit_app._INSUFFICIENT_CSS
    # The ratified green reads keep their own fill (which is also the
    # elite band's — one color language), never a mid-band override.
    gas = dataclasses.replace(_sp_reads(), home_run_per_nine=Decimal("1.75"))
    _, styles = streamlit_app._sp_season_row(gas)
    assert styles["HR/9"] == streamlit_app._HIGHLIGHT


def test_band_registries_cover_every_graded_table() -> None:
    """D-127's "all tables" guard: the grid registry grades every rate
    column the grid carries (the Straight and Oppo Air % fit reads
    deliberately excepted — no quality scale, by decision), and the
    pitcher registry grades every Arms and starter-card metric column."""
    import streamlit_app

    texts, _ = streamlit_app._grid_line_cells(_grid_line(), include_gaps=True)
    rate_columns = {column.removesuffix(" ★") for column in texts} - {
        "AB",
        "H",
        "Barrels",
        "HR",
        "Robbed HR",
        "Straight Air %",  # a fit read (D-128) — no quality scale
        "Oppo Air %",  # the fit read — no quality scale, by decision
    }
    assert rate_columns == set(streamlit_app._GRID_BANDS)
    season_columns = set(streamlit_app._ARMS_METRIC_COLUMNS) - {"PA", "BBE", "HR", "Air %"}
    assert season_columns <= set(streamlit_app._PITCHER_BANDS)
    recent_columns = set(streamlit_app._ARMS_RECENT_METRIC_COLUMNS) - {
        "PA",
        "BBE",
        "HR",
        "HR/9",  # a season read — the two-month cell names its absence
        "xISO",  # same
    }
    assert recent_columns <= set(streamlit_app._PITCHER_BANDS)
    sp_columns = set(streamlit_app._SP_CARD_COLUMNS) - {"Scope", "HR"}
    assert sp_columns <= set(streamlit_app._PITCHER_BANDS)


def test_every_temperature_award_wears_a_band_color() -> None:
    """D-127 on the Conditions tab: the six ratified v2.2 temperature
    awards ARE the six color bands — every award mapped, factor edges at
    the ratified park lines."""
    import streamlit_app

    raws = {raw for _, _, raw in streamlit_app._TEMP_BANDS}
    assert set(streamlit_app._TEMP_AWARD_CSS) == raws
    factor = streamlit_app._FACTOR_BAND
    assert streamlit_app._band_css(factor, 115.0) == streamlit_app._BAND_G3_CSS
    assert streamlit_app._band_css(factor, 110.0) == streamlit_app._BAND_G2_CSS
    assert streamlit_app._band_css(factor, 89.0) == streamlit_app._BAND_R2_CSS
    assert streamlit_app._band_css(factor, 84.0) == streamlit_app._BAND_R3_CSS
    assert streamlit_app._band_css(factor, 100.0) is None


def test_band_edges_print_on_their_surfaces() -> None:
    """D-079 for D-127: every bucket edge prints on its surface — the
    caption fragments build from the same registry the cells grade with,
    and every graded column's hover carries its scale."""
    import streamlit_app

    assert "EV — elite ≥ 91" in streamlit_app._GRID_SCALE_TEXT
    assert "very poor < 85.5" in streamlit_app._GRID_SCALE_TEXT
    assert "HR/9 — elite ≥ 1.5" in streamlit_app._PITCHER_SCALE_TEXT
    assert "Hard-Hit % — elite ≥ 46%" in streamlit_app._PITCHER_SCALE_TEXT
    assert "elite ≤ 18%" in streamlit_app._GRID_SCALE_TEXT  # the low-direction wording
    assert "elite ≥ 91" in streamlit_app._MATCHUPS_HELP["EV"]
    assert "elite ≥ 1.5" in streamlit_app._ARMS_HELP["HR/9"]
    assert "elite ≥ 46%" in streamlit_app._SP_HELP["Hard-Hit %"]
    assert "No cell colors" in streamlit_app._MATCHUPS_HELP["Oppo Air %"]
    assert "No cell colors" in streamlit_app._MATCHUPS_HELP["Straight Air %"]
    assert "115" in streamlit_app._CONDITIONS_HELP["HR factor (LHB)"]


def test_column_help_renames_with_the_grid_stars_and_drops_absent_columns() -> None:
    """D-124: every header carries its one-line definition on hover; the
    star rename matches the grid's own, and a definition naming a column
    the view does not carry drops out rather than confusing the grid."""
    import streamlit_app

    config = streamlit_app._column_help(
        ["Batter", "EV ★", "LA"],
        streamlit_app._MATCHUPS_HELP,
        streamlit_app._GRID_STARS_SEASON,
    )
    assert set(config) == {"Batter", "EV ★", "LA"}
    # The window view stars the spray shares instead; EV keeps its base name.
    window = streamlit_app._column_help(
        ["EV", "Pull Air % ★"],
        streamlit_app._MATCHUPS_HELP,
        streamlit_app._GRID_STARS_WINDOW,
    )
    assert set(window) == {"EV", "Pull Air % ★"}


def _board_with_grid_lines() -> SlateBoard:
    """The graded outage board with populated recent and season grid lines,
    so the matchups grid and its window selector have real figures to show.
    D-128 (PO): the season line carries its own spray profile (Savant's
    published buckets, rebased) and the robbed count shows on both views
    (always the last 7 days)."""
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
        robbed_hr_count=2,
        pull_air_share=Decimal("0.36"),
        straight_air_share=Decimal("0.34"),
        oppo_air_share=Decimal("0.28"),
        avg_launch_angle=Decimal("12.8"),
    )

    def attach(cards: tuple[_BatterCard, ...]) -> tuple[_BatterCard, ...]:
        return tuple(
            _dc.replace(card, mix_line=l30, season_line=season, mix_label="season")
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
    caption names the mix scope actually used (D-025/D-128). D-128 (PO):
    the season sources are the default view — robbed HR and all three air
    profiles show on it — and the recent-window radio swaps the metric
    scope while the grade stays the L30 one."""
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
            if "Robbed HR" in frame.columns:
                frames.append(frame)
        return frames

    grids = grid_frames()
    assert grids, "the matchups grids rendered"
    # D-096/D-097/D-098: no BIP, no Form column; Robbed HR is a count.
    # D-128 (PO): the default view is the season scope — EV starred, the
    # three air profiles and the robbed count all carry season-view values.
    expected = {
        "AB",
        "H",
        "Barrels",
        "HR",
        "EV ★",
        "LA",
        "Barrel/PA %",
        "Hard-Hit %",
        "AVG",
        "SLG",
        "ISO",
        "Robbed HR",
        "Pull Air %",
        "Straight Air %",
        "Oppo Air %",
        "xwOBA",
        "Swing-Str %",
        "Grade",
    }
    assert expected <= set(grids[0].columns)
    assert "BIP" not in grids[0].columns
    assert "Form (EV)" not in grids[0].columns
    assert set(grids[0]["AB"]) == {"440"}  # the season scope is the default
    assert set(grids[0]["Robbed HR"]) == {"2"}  # shows on the season view (D-128)
    assert set(grids[0]["Pull Air %"]) == {"36.0%"}
    assert set(grids[0]["Straight Air %"]) == {"34.0%"}
    assert set(grids[0]["Oppo Air %"]) == {"28.0%"}
    assert set(grids[0]["LA"]) == {"12.8°"}
    season_grades = grids[0]["Grade"].tolist()
    captions = " ".join(element.value for element in at.caption)
    assert "season" in captions  # the mix scope actually used
    assert "14%" in captions
    # D-128 (PO): a More button per batter under each grid — row selection
    # is gone.
    more = [button for button in at.button if button.key.startswith("more_")]
    assert more, "the per-batter More buttons rendered"

    modes = [radio for radio in at.radio if radio.key == "matchups_view_mode"]
    assert modes, "the batter-window selector rendered"
    modes[0].set_value("Recent window")
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    grids = grid_frames()
    assert set(grids[0]["AB"]) == {"5"}  # the recent scope
    assert set(grids[0]["Robbed HR"]) == {"1"}
    # D-124: the recent view stars the two signed spray shares (ratified
    # v2.2 lines); Straight Air % stays unstarred between them.
    assert "Pull Air % ★" in grids[0].columns
    assert "Straight Air %" in grids[0].columns
    assert "Oppo Air % ★" in grids[0].columns
    assert set(grids[0]["Pull Air % ★"]) == {"40.0%"}
    captions = " ".join(element.value for element in at.caption)
    assert "last 28 days" in captions  # the default four weeks
    assert grids[0]["Grade"].tolist() == season_grades  # the fixture's one grade


def test_grid_headers_carry_their_hover_definitions(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-124: every batter-grid header carries its one-line definition as
    column help — starred under the view's own rename, absent columns
    dropped. D-128 (PO): the season view is the default — it stars EV and
    adds LA; the recent window stars the two signed spray shares. D-127:
    the Arms, starter-card and Conditions tables carry their own hover
    definitions now, so the batter-grid assertions scope to the grids
    whose frame has a Batter column."""
    import json

    import streamlit as st

    import greenmachine.live.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_board", lambda **kwargs: _board_with_grid_lines())
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    st.cache_data.clear()
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    def helps(marker: str) -> set[str]:
        names: set[str] = set()
        for element in at.dataframe:
            if marker not in element.value.columns:
                continue
            for name, config in json.loads(element.proto.columns).items():
                if config.get("help"):
                    names.add(name)
        return names

    season = helps("Batter")
    assert {"LA", "EV ★"} <= season
    # D-128: the season view's air profiles carry their hovers unstarred.
    assert "Straight Air %" in season
    assert "Pull Air % ★" not in season
    # D-125: the gap columns left the grid, so their hover entries went too.
    assert "xISO-ISO ★" not in season
    assert "xwOBA-wOBA ★" not in season
    # D-127: the starter cards and the Conditions table carry their hovers.
    assert "BRL%" in helps("Scope")
    assert "Hard-Hit %" in helps("Scope")
    assert "Temp band" in helps("Venue")

    modes = [radio for radio in at.radio if radio.key == "matchups_view_mode"]
    modes[0].set_value("Recent window")
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    recent = helps("Batter")
    assert "Pull Air % ★" in recent
    assert "Straight Air %" in recent
    assert "Oppo Air % ★" in recent
    assert "LA" not in recent  # a season-view column — no entry on the recent grids
    assert "EV ★" not in recent


def test_slate_today_reads_the_viewers_arizona_day() -> None:
    """D-112: the slate's "today" is computed in America/Phoenix (UTC-7
    year-round, no daylight saving), so the server's UTC rollover never
    shows tomorrow's slate as today's."""
    import streamlit_app

    phoenix_today = datetime.now(ZoneInfo("America/Phoenix")).date()
    assert streamlit_app.slate_today() == phoenix_today


def test_slate_nav_regrades_the_chosen_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-101: the calendar date picker chooses the slate date the board
    builds — nothing else about the grading changes. Today, yesterday and
    tomorrow carry their relative word; any other date stands alone.
    D-112: "today" is the viewer's Arizona day, never the server's."""
    import streamlit as st

    import greenmachine.live.pipeline as pipeline

    seen: list[str] = []

    def fake_build(**kwargs: object) -> SlateBoard:
        seen.append(kwargs["slate_date"].isoformat())  # type: ignore[attr-defined]
        return _board_with_grid_lines()

    import streamlit_app

    monkeypatch.setattr(pipeline, "build_board", fake_build)
    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    st.cache_data.clear()
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    today = streamlit_app.slate_today()
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
    """D-109 + D-129: the batter half's contact-shape reads (LA, barrel
    rate, EV, hard-hit, air and both pull reads) carry the ratified 10-BBE
    pitch-type floor — below it the value keeps its exact sample with an
    INSUFFICIENT marker; an empty denominator dashes, never invents."""
    import streamlit_app

    markup = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {
            "FF": _batter_breakup_line(
                batted_balls=7,
                mean_launch_speed=Decimal("91.23"),
                air_ball_share=Decimal("0.5"),
                mean_launch_angle=Decimal("23.4"),
                pull_air_share=Decimal("0.4"),
            )
        },
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert ">EV</th>" in markup
    assert ">LA</th>" in markup
    assert ">Air%</th>" in markup
    assert "91.2 · n=7 · INSUFFICIENT" in markup
    assert "23.4° · n=7 · INSUFFICIENT" in markup
    assert "50.0% · n=7 · INSUFFICIENT" in markup
    assert "40.0% · n=7 · INSUFFICIENT" in markup
    assert "12.0% · n=7 · INSUFFICIENT" in markup
    assert "45.0% · n=7 · INSUFFICIENT" in markup
    # A full sample shows the plain values, no marker.
    markup_full = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {
            "FF": _batter_breakup_line(
                batted_balls=12,
                mean_launch_speed=Decimal("91.23"),
                air_ball_share=Decimal("0.5"),
                mean_launch_angle=Decimal("23.4"),
            )
        },
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    assert ">91.2</td>" in markup_full
    assert ">23.4°</td>" in markup_full
    assert ">50.0%</td>" in markup_full
    assert "INSUFFICIENT" not in markup_full
    # No classified contact at all: dashes, never an invented zero.
    markup_empty = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(),),
        {
            "FF": _batter_breakup_line(
                batted_balls=0,
                mean_launch_speed=None,
                air_ball_share=None,
                mean_launch_angle=None,
                barrel_share=None,
                hard_hit_share=None,
                pull_air_share=None,
                oppo_air_share=None,
            )
        },
        threshold=0.15,
        pitcher_scope_label="season vs LHB",
        batter_scope_label="season vs RHP",
    )
    row = markup_empty.split("4-Seam Fastball", 1)[1].split("</tr>", 1)[0]
    assert row.count("<td>—</td>") >= 2


def test_card_tags_carry_the_slot_and_the_v22_k_reads() -> None:
    """D-109 / v2.2 (D-114): the advisories carry the ordinal lineup slot
    (est.-marked); the K reads re-line to the v2.2 set — the unlock needs
    K% ≥ 22% AND an arsenal whiff ≤ 20%, without that matchup ≥ 28% reads
    binary and ≥ 30% is the high-K caution — never two K tags at once."""
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
        statcast=None,
        sprint_speed_fps=None,
        batting_side=None,
        mix_line=None,
    )
    arm = SimpleNamespace(
        season_whiff_weighted=Decimal("0.20"),
        season_reads=None,
        recent_overall=None,
        throws=None,
    )
    advisories, boosters, vetoes = streamlit_app._card_tags(card, arm)
    assert "est. lineup" in advisories
    # v2.2 (D-115): the leadoff slot is a booster and adds the extra look.
    assert "bats 1st (est.)" in boosters
    assert "extra look at the starter (4-5 PA tier)" in boosters
    assert "high-K bat vs low-whiff arm: K% 28.0 (402 PA), arsenal whiff 20.0%" in boosters
    assert "low-whiff arm: arsenal whiff 20.0% (season)" in boosters
    assert "high-K profile" not in vetoes  # the unlock tag supersedes it
    assert "binary" not in vetoes
    # A normal-whiff arm leaves the binary read at 28%...
    _, boosters, vetoes = streamlit_app._card_tags(
        card,
        SimpleNamespace(
            season_whiff_weighted=Decimal("0.25"),
            season_reads=None,
            recent_overall=None,
            throws=None,
        ),
    )
    assert "binary K profile: K% 28.0 (402 PA)" in vetoes
    assert "low-whiff arm" not in boosters
    # ...and the high-K caution at 30%+.
    hot = SimpleNamespace(**{**vars(card), "season_k_share": Decimal("0.31")})
    _, _, vetoes = streamlit_app._card_tags(
        hot,
        SimpleNamespace(
            season_whiff_weighted=None, season_reads=None, recent_overall=None, throws=None
        ),
    )
    assert "high-K profile: K% 31.0 (402 PA)" in vetoes
    # The 22% unlock line: below it no K tag even against a low-whiff arm.
    quiet = SimpleNamespace(**{**vars(card), "season_k_share": Decimal("0.21")})
    _, boosters, vetoes = streamlit_app._card_tags(quiet, arm)
    assert "high-K" not in boosters
    assert "binary" not in vetoes
    no_line = SimpleNamespace(**{**vars(card), "season_k_share": None, "season": None})
    _, boosters, vetoes = streamlit_app._card_tags(no_line, arm)
    assert "high-K" not in boosters
    assert "binary" not in vetoes and "high-K profile" not in vetoes


def test_card_tags_carry_the_v22_pitcher_side_reads() -> None:
    """v2.2 (D-114, wording per D-116): the pitcher-side tags — the
    ground-ball profile off the L30 event record (extreme ≥ 55%) or the
    season avg-LA line, the HR/9 suppressor, the gas profile (HR/9 ≥ 1.50
    with the L30 GB share under 40%), and the fly-vulnerable flag at
    season avg LA ≥ 18°. The GB% number itself stays on the Arms tab."""
    from types import SimpleNamespace

    import streamlit_app

    card = SimpleNamespace(
        result=SimpleNamespace(present_observations=[], missing_observations=[]),
        order_position=None,
        lineup_is_estimate=False,
        season_k_share=None,
        season=None,
        season_gaps=None,
        squared_up_share=None,
        squared_up_swings=0,
        squared_up_bat_speed=None,
        statcast=None,
        sprint_speed_fps=None,
        batting_side=None,
        mix_line=None,
    )

    def arm(hr9: str, la: str, gb: str | None, bbe: int = 148) -> SimpleNamespace:
        return SimpleNamespace(
            season_whiff_weighted=None,
            season_reads=SimpleNamespace(
                home_run_per_nine=Decimal(hr9), avg_launch_angle=Decimal(la)
            ),
            recent_overall=SimpleNamespace(
                ground_ball_share=Decimal(gb) if gb is not None else None,
                classified_batted_balls=bbe,
            ),
            throws=None,
        )

    # GB profile off the two-month share, plain and extreme — D-116 (PO):
    # the tag fires on the share but never quotes the GB% number. D-128
    # (PO): the record behind it is the last two months now.
    _, _, vetoes = streamlit_app._card_tags(card, arm("1.10", "10.2", "0.52"))
    assert "air allowed: low — ground-ball profile (2-month record)" in vetoes
    assert "52.0%" not in vetoes
    _, _, vetoes = streamlit_app._card_tags(card, arm("1.10", "10.2", "0.56"))
    assert "extreme ground-ball profile (2-month record)" in vetoes
    # The season LA line carries it when the two-month share is unpublished.
    _, _, vetoes = streamlit_app._card_tags(card, arm("1.10", "7.8", None))
    assert "air allowed: low — ground-ball profile (avg LA 7.8°, season)" in vetoes
    # Suppressor, gas, and fly-vulnerable.
    _, _, vetoes = streamlit_app._card_tags(card, arm("0.75", "11.0", "0.44"))
    assert "suppressor: HR/9 0.75 (season)" in vetoes
    _, boosters, _ = streamlit_app._card_tags(card, arm("1.62", "11.0", "0.35"))
    assert "gas: HR/9 1.62 (season)" in boosters
    assert "35.0%" not in boosters
    _, boosters, _ = streamlit_app._card_tags(card, arm("1.62", "11.0", "0.45"))
    assert "gas" not in boosters
    _, boosters, _ = streamlit_app._card_tags(card, arm("1.10", "18.4", "0.44"))
    assert "fly-ball vulnerable: avg LA 18.4° (season)" in boosters
    # A neutral arm fires none of the pitcher-side tags.
    _, boosters, vetoes = streamlit_app._card_tags(card, arm("1.10", "11.0", "0.44"))
    assert boosters == "" and vetoes == ""
    # No opposing arm at all: no pitcher-side tags, no error.
    _, boosters, vetoes = streamlit_app._card_tags(card, None)
    assert boosters == "" and vetoes == ""


def test_card_tags_carry_the_v22_x_gap_and_contact_first_reads() -> None:
    """v2.2 (D-115), superseding D-110: the x-gap flag is under-performance
    evidence — the positive side only, xISO-ISO ≥ +.050 or xwOBA-wOBA
    ≥ +.015, both values always shown with the PA sample, riding the green
    column; contact-first flips to a veto — squared-up ≥ 35% of competitive
    swings with a SUB-70 bat speed, a contact profile, not power."""
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
        statcast=None,
        sprint_speed_fps=None,
        batting_side=None,
        mix_line=None,
        team="",
        form=None,
    )
    # The xISO side trips the flag; the other value still prints, with the
    # D-125 reliability band riding the sample.
    over = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("0.051"),
                xwoba_minus_woba=Decimal("-0.012"),
                plate_appearances=412,
            ),
        }
    )
    _, boosters, _ = streamlit_app._card_tags(over, None)
    assert "x-gap: xISO +.051, xwOBA -.012 (season, 412 PA · established)" in boosters
    # The xwOBA side trips it at its own, lighter line.
    flipped = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("0.010"),
                xwoba_minus_woba=Decimal("0.015"),
                plate_appearances=88,
            ),
        }
    )
    assert "x-gap" in streamlit_app._card_tags(flipped, None)[1]
    # A NEGATIVE gap (over-performance) is not the under-performance flag.
    negative = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("-0.060"),
                xwoba_minus_woba=Decimal("-0.020"),
                plate_appearances=88,
            ),
        }
    )
    assert "x-gap" not in streamlit_app._card_tags(negative, None)[1]
    # Under both lines, and no board row: no tag.
    under = SimpleNamespace(
        **{
            **base,
            "season_gaps": RegressionGaps(
                xiso_minus_iso=Decimal("0.049"),
                xwoba_minus_woba=Decimal("0.014"),
                plate_appearances=88,
            ),
        }
    )
    assert "x-gap" not in streamlit_app._card_tags(under, None)[1]
    assert "x-gap" not in streamlit_app._card_tags(SimpleNamespace(**base), None)[1]
    # Contact-first veto: squared-up high AND a sub-70 bat speed, both.
    contact = SimpleNamespace(
        **{
            **base,
            "squared_up_share": Decimal("0.362"),
            "squared_up_swings": 620,
            "squared_up_bat_speed": Decimal("68.4"),
        }
    )
    _, _, vetoes = streamlit_app._card_tags(contact, None)
    assert "contact-first profile: squared-up 36.2% (620 swings), bat speed 68.4 mph" in vetoes
    fast_bat = SimpleNamespace(**{**vars(contact), "squared_up_bat_speed": Decimal("70.1")})
    assert "contact-first" not in streamlit_app._card_tags(fast_bat, None)[2]
    low_squared = SimpleNamespace(**{**vars(contact), "squared_up_share": Decimal("0.349")})
    assert "contact-first" not in streamlit_app._card_tags(low_squared, None)[2]


def test_card_tags_carry_the_v22_batter_boosters() -> None:
    """v2.2 (D-115): barrel elite (≥ 15% over ≥ 50 season BBE), the power
    profile (EV ≥ 91 + bat speed ≥ 73), the platoon advantage off the
    resolved side, the robbed count from the D-113 column, and the top-5
    slot — all riding the green column with their samples."""
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
        statcast=None,
        sprint_speed_fps=None,
        batting_side=None,
        mix_line=None,
        team="",
        form=None,
    )

    def batter(**over: object) -> SimpleNamespace:
        return SimpleNamespace(**{**base, **over})

    def statcast(bbe: int, barrel: str, ev: str) -> SimpleNamespace:
        return SimpleNamespace(
            batted_ball_events=bbe,
            barrel_share=Decimal(barrel),
            exit_velocity_avg=Decimal(ev),
        )

    arm = SimpleNamespace(
        season_whiff_weighted=None, season_reads=None, recent_overall=None, throws="R"
    )
    # Barrel elite with the gate met; below the BBE gate it stays silent.
    slugger = batter(statcast=statcast(320, "0.161", "90.2"), batting_side="L")
    _, boosters, _ = streamlit_app._card_tags(slugger, arm)
    assert "barrel 16.1% (320 BBE)" in boosters
    thin = batter(statcast=statcast(49, "0.161", "90.2"))
    assert "barrel" not in streamlit_app._card_tags(thin, arm)[1]
    # The power profile needs BOTH sides of the line.
    _, boosters, _ = streamlit_app._card_tags(
        batter(statcast=statcast(320, "0.09", "91.4"), squared_up_bat_speed=Decimal("73.5")),
        arm,
    )
    assert "power profile: EV 91.4 mph, bat speed 73.5 mph (season)" in boosters
    _, boosters, _ = streamlit_app._card_tags(
        batter(statcast=statcast(320, "0.09", "91.4"), squared_up_bat_speed=Decimal("72.9")),
        arm,
    )
    assert "power profile" not in boosters
    # Platoon advantage off the resolved side; same-side stays silent.
    _, boosters, _ = streamlit_app._card_tags(batter(batting_side="L"), arm)
    assert "platoon advantage: bats L vs RP" in boosters
    _, boosters, _ = streamlit_app._card_tags(batter(batting_side="R"), arm)
    assert "platoon" not in boosters
    # Robbed rides the D-113 count — one or more, never a rate, 0 silent.
    _, boosters, _ = streamlit_app._card_tags(
        batter(mix_line=SimpleNamespace(robbed_hr_count=2)), arm
    )
    assert "robbed: 2 at 375+ ft stayed in the park (L7)" in boosters
    _, boosters, _ = streamlit_app._card_tags(
        batter(mix_line=SimpleNamespace(robbed_hr_count=0)), arm
    )
    assert "robbed" not in boosters
    # Top-5 slot is a booster; the 7-hole stays an advisory.
    _, boosters, _ = streamlit_app._card_tags(batter(order_position=4), arm)
    assert "bats 4th" in boosters
    advisories, boosters, _ = streamlit_app._card_tags(batter(order_position=7), arm)
    assert "bats 7th" in advisories and "bats 7th" not in boosters
    # Actual over expected: context only, on the neutral column — D-125
    # names the structural reasons present, no reason no tag.
    context = batter(
        season_gaps=RegressionGaps(
            xiso_minus_iso=Decimal("-0.030"),
            xwoba_minus_woba=Decimal("-0.042"),
            plate_appearances=401,
        ),
        sprint_speed_fps=Decimal("28.4"),
    )
    advisories, _, _ = streamlit_app._card_tags(context, arm)
    assert (
        "actual over expected: wOBA +.042 over xwOBA (season, 401 PA · established) "
        "— likely structural: sprint 28.4 ft/s; "
        "x-stats are park-neutral and direction-blind" in advisories
    )
    slow = SimpleNamespace(**{**vars(context), "sprint_speed_fps": Decimal("27.1")})
    assert "actual over expected" not in streamlit_app._card_tags(slow, arm)[0]


def test_card_tags_carry_the_d125_bands_and_why_riders() -> None:
    """D-125 (PO): every gap read carries its reliability band (thin under
    200 PA, readable 200-399, established 400+ — builder bands off the
    ratified stabilization anchors, printed in the captions per D-079).
    The under-performance tag adds a rider when the batter's home park
    suppresses HRs on his side (the park-neutral x-stats can hold that gap
    open); the over-performance advisory names every structural reason
    present — sprint, a pull-heavy air profile, a boosting home park."""
    from types import SimpleNamespace

    import streamlit_app

    from greenmachine.live.pipeline import RegressionGaps

    assert streamlit_app._gap_band(0) == "thin"
    assert streamlit_app._gap_band(199) == "thin"
    assert streamlit_app._gap_band(200) == "readable"
    assert streamlit_app._gap_band(399) == "readable"
    assert streamlit_app._gap_band(400) == "established"

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
        statcast=None,
        sprint_speed_fps=None,
        batting_side="L",
        mix_line=None,
        team="",
        form=None,
    )

    def batter(**over: object) -> SimpleNamespace:
        return SimpleNamespace(**{**base, **over})

    def gaps(xwoba: str, pa: int = 412) -> RegressionGaps:
        return RegressionGaps(
            xiso_minus_iso=Decimal("0.051"),
            xwoba_minus_woba=Decimal(xwoba),
            plate_appearances=pa,
        )

    # The band text rides the sample: 88 PA reads thin.
    _, boosters, _ = streamlit_app._card_tags(batter(season_gaps=gaps("-0.012", 88)), None)
    assert "(season, 88 PA · thin)" in boosters
    # A suppressive home park (Oracle, LHB factor 73) attaches the rider.
    _, boosters, _ = streamlit_app._card_tags(
        batter(season_gaps=gaps("-0.012"), team="San Francisco Giants"), None
    )
    assert "home park HR factor 73 (LHB) can hold the gap open" in boosters
    # A neutral home park or an unresolved side stays rider-free.
    _, boosters, _ = streamlit_app._card_tags(
        batter(season_gaps=gaps("-0.012"), team="New York Mets"), None
    )
    assert "can hold the gap open" not in boosters
    _, boosters, _ = streamlit_app._card_tags(
        batter(season_gaps=gaps("-0.012"), team="San Francisco Giants", batting_side=None),
        None,
    )
    assert "can hold the gap open" not in boosters
    # Over-performance: the pull-heavy air profile and the boosting home
    # park join the sprint reason; all three print when all three fire.
    form = SimpleNamespace(
        pull_air_pct=SimpleNamespace(
            sufficient=True, value=Decimal("44.2"), sample=19, window_days=14
        )
    )
    advisories, _, _ = streamlit_app._card_tags(
        batter(
            season_gaps=gaps("-0.045"),
            sprint_speed_fps=Decimal("28.4"),
            form=form,
            team="Los Angeles Dodgers",
            batting_side="R",
        ),
        None,
    )
    assert "sprint 28.4 ft/s" in advisories
    assert "pull-air 44% (19 air balls L14)" in advisories
    assert "home park HR factor 132 (RHB)" in advisories
    assert "park-neutral and direction-blind" in advisories
    # An insufficient spray record drops only its own reason.
    thin_form = SimpleNamespace(
        pull_air_pct=SimpleNamespace(sufficient=False, value=None, sample=4, window_days=14)
    )
    advisories, _, _ = streamlit_app._card_tags(
        batter(season_gaps=gaps("-0.045"), sprint_speed_fps=Decimal("28.4"), form=thin_form),
        None,
    )
    assert "sprint 28.4 ft/s" in advisories and "pull-air" not in advisories


def test_card_tags_carry_the_v22_park_and_weather_reads() -> None:
    """v2.2 (D-118): the park boost at a batter-side HR factor ≥ 110
    (strong ≥ 115), the wrong-side park at ≤ 90 (strong ≤ 85), the heat
    boost at ≥ 85°F (strong ≥ 90°F), and the cold suppress below 45°F —
    open-air venues only; a roof or a missing game keeps the tags silent."""
    from types import SimpleNamespace

    import streamlit_app

    from greenmachine.inputs.contract import VenueType

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
        statcast=None,
        sprint_speed_fps=None,
        batting_side="L",
        mix_line=None,
        form=None,
    )

    def batter(**over: object) -> SimpleNamespace:
        return SimpleNamespace(**{**base, **over})

    def game(factor_l: str, temp: str | None, venue: VenueType = VenueType.OPEN_AIR):
        return SimpleNamespace(
            venue_type=venue,
            temperature_fahrenheit=Decimal(temp) if temp is not None else None,
            home_run_factor_left=ParkFactor(
                factor=Decimal(factor_l),
                handedness=Handedness.LEFT,
                plate_appearances=30000,
            ),
            home_run_factor_right=ParkFactor(
                factor=Decimal("100"),
                handedness=Handedness.RIGHT,
                plate_appearances=30000,
            ),
            park_orientation_degrees=None,
            wind_from_degrees=None,
            wind_speed_mph=None,
            wind_direction=None,
        )

    # The park reads fire off the batter's resolved side, with the strong
    # variants past their own lines; a neutral factor stays silent.
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("112", "72"))
    assert "park boost: HR factor 112 (LHB)" in boosters
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("118", "72"))
    assert "park boost: strong HR factor 118 (LHB)" in boosters
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game("88", "72"))
    assert "wrong-side park: HR factor 88 (LHB)" in vetoes
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game("84", "72"))
    assert "wrong-side park: strong HR factor 84 (LHB)" in vetoes
    tags = streamlit_app._card_tags(batter(), None, game=game("100", "72"))
    assert "park" not in tags[1] and "park" not in tags[2]
    # The right-handed read takes the right-side factor, not the left.
    _, boosters, _ = streamlit_app._card_tags(
        batter(batting_side="R"), None, game=game("118", "72")
    )
    assert "park boost" not in boosters
    # The weather reads: heat at 85/90, cold below 45, open air only.
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("100", "87"))
    assert "heat boost: 87°F" in boosters
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("100", "93"))
    assert "heat boost: strong 93°F" in boosters
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game("100", "41"))
    assert "cold suppress: 41°F" in vetoes
    tags = streamlit_app._card_tags(batter(), None, game=game("100", "72"))
    assert "heat" not in tags[1] and "cold" not in tags[2]
    # A roof is the indoor neutral value — no weather reads at any temp.
    tags = streamlit_app._card_tags(batter(), None, game=game("100", "93", VenueType.FIXED_ROOF))
    assert "heat" not in tags[1]
    tags = streamlit_app._card_tags(
        batter(), None, game=game("100", "38", VenueType.RETRACTABLE_ROOF)
    )
    assert "cold" not in tags[2]
    # A missing temperature or a missing game is a silent tag, never an
    # invented one.
    tags = streamlit_app._card_tags(batter(), None, game=game("100", None))
    assert "heat" not in tags[1] and "cold" not in tags[2]
    tags = streamlit_app._card_tags(batter(), None)
    assert "park" not in tags[1] and "heat" not in tags[1]
    assert "park" not in tags[2] and "cold" not in tags[2]


def test_card_tags_resolve_the_wind_against_the_dominant_air_field() -> None:
    """SP-4 (D-119): the wind assist at ≥ 8 mph resolved out toward the
    batter's dominant air field (strong ≥ 12), the wind kill at ≥ 10 mph
    resolved in from it or ≥ 8 mph resolved out to the opposite corner,
    and the severe cold suppress below 38°F with an in-wind ≥ 5 mph along
    the axis. A roof, an unmeasured axis, an unparseable compass reading,
    or an insufficient spray record keeps the wind tags silent."""
    from types import SimpleNamespace

    import streamlit_app

    from greenmachine.inputs.contract import VenueType
    from greenmachine.live.form import FormValue

    def spray(pull: str, oppo: str, *, sufficient: bool = True) -> SimpleNamespace:
        return SimpleNamespace(
            pull_air_pct=FormValue(
                value=Decimal(pull), sample=10, window_days=7, sufficient=sufficient
            ),
            oppo_air_pct=FormValue(
                value=Decimal(oppo), sample=10, window_days=7, sufficient=sufficient
            ),
        )

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
        statcast=None,
        sprint_speed_fps=None,
        batting_side="L",
        mix_line=None,
        form=spray("45", "20"),  # pull 45 / center 35 / oppo 20 — pull-dominant
    )

    def batter(**over: object) -> SimpleNamespace:
        return SimpleNamespace(**{**base, **over})

    def game(
        wind_from: str | None,
        speed: str | None,
        compass: str | None = "SSW",
        temp: str = "72",
        axis: str | None = "0",
        venue: VenueType = VenueType.OPEN_AIR,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            venue_type=venue,
            temperature_fahrenheit=Decimal(temp),
            home_run_factor_left=None,
            home_run_factor_right=None,
            park_orientation_degrees=Decimal(axis) if axis is not None else None,
            wind_from_degrees=Decimal(wind_from) if wind_from is not None else None,
            wind_speed_mph=Decimal(speed) if speed is not None else None,
            wind_direction=compass,
        )

    # The assist resolves the forecast toward his field: a LHB's pull is
    # right field at axis+30, so a wind FROM 210 blows straight out there.
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("210", "9"))
    assert "wind assist: 9 mph out to right (SSW 9 mph)" in boosters
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("210", "13"))
    assert "wind assist: strong 13 mph out to right (SSW 13 mph)" in boosters
    # A right-hander's pull is left field — the name mirrors, and the
    # bearing does too (axis-30 = 330, out wind FROM 150).
    _, boosters, _ = streamlit_app._card_tags(batter(batting_side="R"), None, game=game("150", "9"))
    assert "wind assist: 9 mph out to left (SSW 9 mph)" in boosters
    # The kill: ≥ 10 mph resolved in from his field (wind FROM 30).
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game("30", "11", compass="NNE"))
    assert "wind kill: 11 mph in from right (NNE 11 mph)" in vetoes
    # ... or ≥ 8 mph resolved out to the opposite corner while doing
    # neither toward his own (FROM 150: 4.5 mph toward his field at 30°,
    # a straight 9 mph out to left at 330°).
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game("150", "9"))
    assert "wind kill: 9 mph out to left, away from his air field (SSW 9 mph)" in vetoes
    # Between the lines nothing fires: 6 mph out is under the assist line.
    tags = streamlit_app._card_tags(batter(), None, game=game("210", "6"))
    assert "wind" not in tags[1] and "wind" not in tags[2]
    # A center-dominant spray has no opposite corner — a crosswind that
    # resolves nowhere near his field stays silent.
    tags = streamlit_app._card_tags(batter(form=spray("30", "30")), None, game=game("150", "9"))
    assert "wind" not in tags[1] and "wind" not in tags[2]
    # The severe cold suppress needs the in-wind along the axis and never
    # reads the spray record; the plain cold read survives a calm night.
    _, _, vetoes = streamlit_app._card_tags(
        batter(form=None), None, game=game("0", "6", compass="N", temp="35")
    )
    assert "cold suppress: severe 35°F + wind in 6 mph" in vetoes
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game(None, None, temp="41"))
    assert "cold suppress: 41°F" in vetoes
    _, _, vetoes = streamlit_app._card_tags(batter(), None, game=game("0", "3", temp="35"))
    assert "cold suppress: 35°F" in vetoes
    assert "severe" not in vetoes
    # Silence: a roof, an unmeasured axis, an unparseable compass reading,
    # or a spray record under the floors.
    tags = streamlit_app._card_tags(
        batter(), None, game=game("210", "13", venue=VenueType.RETRACTABLE_ROOF)
    )
    assert "wind" not in tags[1] and "wind" not in tags[2]
    tags = streamlit_app._card_tags(batter(), None, game=game("210", "13", axis=None))
    assert "wind" not in tags[1] and "wind" not in tags[2]
    tags = streamlit_app._card_tags(batter(), None, game=game(None, "13", compass="Variable"))
    assert "wind" not in tags[1] and "wind" not in tags[2]
    tags = streamlit_app._card_tags(
        batter(form=spray("45", "20", sufficient=False)), None, game=game("210", "13")
    )
    assert "wind" not in tags[1] and "wind" not in tags[2]
    tags = streamlit_app._card_tags(batter(form=None), None, game=game("210", "13"))
    assert "wind" not in tags[1] and "wind" not in tags[2]


def test_card_tags_carry_the_spray_alignment_reads() -> None:
    """v2.2 (D-120): the pull-air match at a pull share ≥ 40% with the
    same-side HR factor ≥ 110, and the oppo-air match at an oppo share
    strictly over 20% against the OPPOSITE-side factor (the Walker
    exception — an oppo-power bat reads as the other hand for the park).
    The "+ wind" rider joins when the forecast resolves out to the
    matching field at ≥ 8 mph. An insufficient spray record or a neutral
    factor keeps the tags silent."""
    from types import SimpleNamespace

    import streamlit_app

    from greenmachine.inputs.contract import VenueType
    from greenmachine.live.form import FormValue

    def spray(pull: str, oppo: str, *, sufficient: bool = True) -> SimpleNamespace:
        return SimpleNamespace(
            pull_air_pct=FormValue(
                value=Decimal(pull), sample=10, window_days=7, sufficient=sufficient
            ),
            oppo_air_pct=FormValue(
                value=Decimal(oppo), sample=10, window_days=7, sufficient=sufficient
            ),
        )

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
        statcast=None,
        sprint_speed_fps=None,
        batting_side="L",
        mix_line=None,
        form=spray("45", "18"),
    )

    def batter(**over: object) -> SimpleNamespace:
        return SimpleNamespace(**{**base, **over})

    def game(
        factor_l: str,
        factor_r: str,
        wind_from: str | None = None,
        speed: str | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            venue_type=VenueType.OPEN_AIR,
            temperature_fahrenheit=Decimal("72"),
            home_run_factor_left=ParkFactor(
                factor=Decimal(factor_l),
                handedness=Handedness.LEFT,
                plate_appearances=30000,
            ),
            home_run_factor_right=ParkFactor(
                factor=Decimal(factor_r),
                handedness=Handedness.RIGHT,
                plate_appearances=30000,
            ),
            park_orientation_degrees=Decimal("0"),
            wind_from_degrees=Decimal(wind_from) if wind_from is not None else None,
            wind_speed_mph=Decimal(speed) if speed is not None else None,
            wind_direction="SSW",
        )

    # The pull match: his side's factor at the boost line, pull share
    # over 40 — the tag quotes the floored form sample.
    _, boosters, _ = streamlit_app._card_tags(batter(), None, game=game("112", "100"))
    assert "pull-air match: 45% pull air (10 air balls L7), LHB factor 112" in boosters
    # The wind rider: FROM 210 blows straight out to his pull field at 30°.
    _, boosters, _ = streamlit_app._card_tags(
        batter(), None, game=game("112", "100", wind_from="210", speed="9")
    )
    assert "LHB factor 112, wind 9 mph out to right" in boosters
    # A neutral park or a pull share under the line stays silent.
    tags = streamlit_app._card_tags(batter(), None, game=game("100", "100"))
    assert "pull-air" not in tags[1]
    tags = streamlit_app._card_tags(batter(form=spray("39", "18")), None, game=game("112", "100"))
    assert "pull-air" not in tags[1]
    # The oppo match reads the OTHER side's factor — a right-hander with
    # oppo power reads as a left-hander for the park.
    _, boosters, _ = streamlit_app._card_tags(
        batter(batting_side="R", form=spray("30", "24")), None, game=game("115", "98")
    )
    assert "oppo-air match: 24% oppo air (10 air balls L7), reads as LHB: factor 115" in boosters
    # ... strictly over 20, and silent against a neutral opposite side.
    tags = streamlit_app._card_tags(
        batter(batting_side="R", form=spray("30", "20")), None, game=game("115", "98")
    )
    assert "oppo-air" not in tags[1]
    tags = streamlit_app._card_tags(
        batter(batting_side="R", form=spray("30", "24")), None, game=game("100", "112")
    )
    assert "oppo-air" not in tags[1]
    # The oppo wind rider: his oppo field sits at axis+30, so FROM 210
    # blows straight out there.
    _, boosters, _ = streamlit_app._card_tags(
        batter(batting_side="R", form=spray("30", "24")),
        None,
        game=game("115", "98", wind_from="210", speed="9"),
    )
    assert "factor 115, wind 9 mph out to right" in boosters
    # An insufficient spray record silences both reads.
    tags = streamlit_app._card_tags(
        batter(form=spray("45", "24", sufficient=False)), None, game=game("115", "112")
    )
    assert "pull-air" not in tags[1] and "oppo-air" not in tags[1]


def test_temp_band_labels_follow_the_ratified_edges() -> None:
    """v2.2 (D-121): the Conditions tab's temperature bands — <45 → 0,
    45-64 → 0.25, 65-74 → 0.5, 75-84 → 1, 85-89 → 1.25, ≥90 → 1.5 — with
    the cap named on the hot bands, lower-inclusive at every edge."""
    import streamlit_app

    assert streamlit_app._temp_band(Decimal("44.9")) == "<45 → 0"
    assert streamlit_app._temp_band(Decimal("20")) == "<45 → 0"
    assert streamlit_app._temp_band(Decimal("45")) == "45-64 → 0.25"
    assert streamlit_app._temp_band(Decimal("64.9")) == "45-64 → 0.25"
    assert streamlit_app._temp_band(Decimal("65")) == "65-74 → 0.5"
    assert streamlit_app._temp_band(Decimal("72")) == "65-74 → 0.5"
    assert streamlit_app._temp_band(Decimal("75")) == "75-84 → 1"
    assert streamlit_app._temp_band(Decimal("84.9")) == "75-84 → 1"
    assert streamlit_app._temp_band(Decimal("85")) == "85-89 → 1.25 · capped at 1"
    assert streamlit_app._temp_band(Decimal("89.9")) == "85-89 → 1.25 · capped at 1"
    assert streamlit_app._temp_band(Decimal("90")) == "≥90 → 1.5 · capped at 1"
    assert streamlit_app._temp_band(Decimal("104")) == "≥90 → 1.5 · capped at 1"


def test_wind_effect_css_colours_only_receptive_aligned_wind() -> None:
    """D-122 (D-082's colour rule): green when the current-direction wind
    helps at a wind-receptive park, red when it hurts — direction-specific,
    because the model's signs differ by direction at the same park — and
    neutral when calm, barely-affected, or unread."""
    import streamlit_app

    from greenmachine.inputs.wind_receptiveness import WindReceptiveness

    wrigley = WindReceptiveness(
        recept_in=Decimal("4.72"), recept_out=Decimal("4.43"), recept_overall=Decimal("9.15")
    )
    angel = WindReceptiveness(
        recept_in=Decimal("3.32"), recept_out=Decimal("-2.36"), recept_overall=Decimal("0.96")
    )
    daikin = WindReceptiveness(
        recept_in=Decimal("-3.21"), recept_out=Decimal("1.83"), recept_overall=Decimal("-1.38")
    )
    quiet = WindReceptiveness(
        recept_in=Decimal("0.62"), recept_out=Decimal("0.40"), recept_overall=Decimal("0.50")
    )

    # Wrigley's modelled receptiveness is positive in BOTH directions —
    # the colour follows the direction-specific figure, not intuition
    # about what an in-wind "should" do.
    assert streamlit_app._wind_effect_css(wrigley, Decimal("7")) == streamlit_app._HIGHLIGHT
    assert streamlit_app._wind_effect_css(wrigley, Decimal("-7")) == streamlit_app._HIGHLIGHT
    # Angel's out-wind suppresses the HR environment even though its
    # in-wind helps — the overall figure would mislead.
    assert streamlit_app._wind_effect_css(angel, Decimal("7")) == streamlit_app._VETO_CSS
    assert streamlit_app._wind_effect_css(angel, Decimal("-7")) == streamlit_app._HIGHLIGHT
    # Daikin's in-wind suppresses while its out-wind helps.
    assert streamlit_app._wind_effect_css(daikin, Decimal("-7")) == streamlit_app._VETO_CSS
    assert streamlit_app._wind_effect_css(daikin, Decimal("7")) == streamlit_app._HIGHLIGHT
    # Calm, barely-affected, and unread all stay neutral.
    assert streamlit_app._wind_effect_css(wrigley, Decimal("3.9")) == ""
    assert streamlit_app._wind_effect_css(quiet, Decimal("9")) == ""
    assert streamlit_app._wind_effect_css(None, Decimal("9")) == ""
    assert streamlit_app._wind_effect_css(wrigley, None) == ""


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
    structure. D-129: the scope labels land in the half headers."""
    import streamlit_app

    markup = streamlit_app._arsenal_breakup_html(
        (_pitcher_breakup_line(pitch_name="<b>Fastball</b>"),),
        {},
        threshold=0.15,
        pitcher_scope_label="season, all hands",
        batter_scope_label="season, all hands",
    )
    assert "<b>Fastball</b>" not in markup
    assert "&lt;b&gt;Fastball&lt;/b&gt;" in markup
    assert "Pitcher — season, all hands" in markup
    assert "Batter — season, all hands" in markup
