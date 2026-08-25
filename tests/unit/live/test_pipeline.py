"""Slate assembly and grading over fake adapters (GMF-006).

Every source is scripted: no network, no clock beyond the injected ``as_of``.
The config under test is the approved production one — the same file the
deployed app loads — so these tests also guard the config against drift.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from greenmachine.config.loader import load_config
from greenmachine.domain.enums import ComponentId, MissingReason, SampleStatus
from greenmachine.domain.grade_result import EvaluatedGradeResult
from greenmachine.inputs.contract import Handedness, ParkFactor
from greenmachine.live.form import MIN_BBE_FORM
from greenmachine.live.mlb_api import (
    BattingOrders,
    FetchFailure,
    GameLogEntry,
    PitchingLogEntry,
    ProbablePitcher,
    ScheduledGame,
    SeasonHittingLine,
    SeasonPitchingLine,
    Slate,
)
from greenmachine.live.pipeline import _starter_workload, _stuff_drift, build_board
from greenmachine.live.savant import (
    BattedBallRow,
    BatTrackingRow,
    ExpectedStatsRow,
    PitchArsenalRow,
    PitchEvent,
    SprintSpeedRow,
    SquaredUpRow,
    StatcastBatterRow,
    StatcastPitcherRow,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_config(REPO_ROOT / "config" / "production" / "gm_hr_v1.yaml")

SLATE_DATE = date(2026, 8, 20)
AS_OF = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)

BATTER_ID = 101
PITCHER_ID = 201


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


def _season_hitting(player_id: int, bats: str = "L") -> SeasonHittingLine:
    return SeasonHittingLine(
        player_id=player_id,
        full_name=f"Batter {player_id}",
        bats=bats,
        games=120,
        plate_appearances=500,
        at_bats=440,
        hits=121,
        home_runs=33,
        strikeouts=130,
    )


def _statcast_row(player_id: int) -> StatcastBatterRow:
    return StatcastBatterRow(
        player_id=player_id,
        batted_ball_events=300,
        exit_velocity_avg=Decimal("91.5"),
        hard_hit_count=150,
        hard_hit_share=Decimal("0.5"),
        barrel_count=30,
        barrel_share=Decimal("0.1"),
        sweet_spot_share=Decimal("0.33"),
        avg_launch_angle=Decimal("16.4"),
    )


def _tracking_row(player_id: int, side: str = "L") -> BatTrackingRow:
    return BatTrackingRow(
        player_id=player_id,
        side=side,
        avg_bat_speed=Decimal("74"),
        attack_angle=Decimal("12"),
        ideal_attack_angle_share=Decimal("0.6"),
        competitive_swings=300,
    )


def _arsenal_row(
    player_id: int, pitch_type: str, usage: str, woba: str, whiff: str, put_away: str
) -> PitchArsenalRow:
    return PitchArsenalRow(
        player_id=player_id,
        team="ARI" if player_id == BATTER_ID else "LAD",
        pitch_type=pitch_type,
        pitch_name=pitch_type,
        pitches=400,
        usage_share=Decimal(usage),
        plate_appearances=100,
        batting_average=Decimal("0.250"),
        slugging=Decimal("0.400"),
        woba=Decimal(woba),
        whiff_share=Decimal(whiff),
        strikeout_share=Decimal("0.2"),
        put_away_share=Decimal(put_away),
        expected_woba=Decimal(woba),
        hard_hit_share=Decimal("0.4"),
    )


def _recent_events() -> tuple[PitchEvent, ...]:
    return tuple(
        PitchEvent(
            game_pk=777000,
            game_date="2026-08-19",
            batter_id=BATTER_ID,
            pitcher_id=PITCHER_ID,
            batter_side="L",
            pitcher_throws="R",
            pitch_type="FF",
            event="single",
            description="",
            bb_type="fly_ball",
            launch_speed=Decimal("96"),
            launch_angle=Decimal("20"),
            launch_speed_angle=6,
            hc_x=Decimal("150"),
            hc_y=Decimal("150"),
            estimated_woba=None,
            woba_value=Decimal("0.9"),
            woba_denom=Decimal("1"),
        )
        for _ in range(MIN_BBE_FORM)
    )


class _FakeApi:
    def __init__(
        self,
        *,
        orders: BattingOrders | FetchFailure | None = None,
        hitting: dict[int, SeasonHittingLine] | None = None,
        pitching: dict[int, SeasonPitchingLine] | None = None,
        game_logs: dict[int, tuple[GameLogEntry, ...]] | FetchFailure | None = None,
        pitching_logs: dict[int, tuple[PitchingLogEntry, ...]] | FetchFailure | None = None,
    ) -> None:
        self._orders = orders
        self._game_logs = game_logs
        self._pitching_logs = pitching_logs
        self._hitting = hitting if hitting is not None else {BATTER_ID: _season_hitting(BATTER_ID)}
        self._pitching = (
            pitching
            if pitching is not None
            else {
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
        )

    def fetch_slate(self, date_mmddyyyy: str) -> Slate:
        return Slate(official_date="2026-08-20", games=(_game(),))

    def fetch_batting_orders(self, game_pk: int) -> BattingOrders | FetchFailure:
        if self._orders is not None:
            return self._orders
        return BattingOrders(game_pk=game_pk, home=(BATTER_ID,), away=(BATTER_ID,))

    def fetch_season_hitting(self, player_ids: tuple[int, ...]) -> dict[int, SeasonHittingLine]:
        return {pid: line for pid, line in self._hitting.items() if pid in player_ids}

    def fetch_season_pitching(self, player_ids: tuple[int, ...]) -> dict[int, SeasonPitchingLine]:
        return {pid: line for pid, line in self._pitching.items() if pid in player_ids}

    def fetch_recent_game_logs(
        self, player_ids: tuple[int, ...], start_mmddyyyy: str, end_mmddyyyy: str
    ) -> dict[int, tuple[GameLogEntry, ...]] | FetchFailure:
        if self._game_logs is None:
            return {}
        if isinstance(self._game_logs, FetchFailure):
            return self._game_logs
        return {pid: log for pid, log in self._game_logs.items() if pid in player_ids}

    def fetch_recent_pitching_logs(
        self, player_ids: tuple[int, ...], start_mmddyyyy: str, end_mmddyyyy: str
    ) -> dict[int, tuple[PitchingLogEntry, ...]] | FetchFailure:
        if self._pitching_logs is None:
            return {}
        if isinstance(self._pitching_logs, FetchFailure):
            return self._pitching_logs
        return {pid: log for pid, log in self._pitching_logs.items() if pid in player_ids}


class _FakeSavant:
    def __init__(
        self,
        *,
        batter_arsenal: tuple[PitchArsenalRow, ...] | FetchFailure = (),
        pitcher_arsenal: tuple[PitchArsenalRow, ...] | FetchFailure = (),
        expected: dict[int, ExpectedStatsRow] | FetchFailure | None = None,
        sprint: dict[int, SprintSpeedRow] | FetchFailure | None = None,
        squared: dict[int, SquaredUpRow] | FetchFailure | None = None,
        pitcher_expected: dict[int, ExpectedStatsRow] | FetchFailure | None = None,
        pitcher_statcast: dict[int, StatcastPitcherRow] | FetchFailure | None = None,
        statcast: dict[int, StatcastBatterRow] | FetchFailure | None = None,
        batted_ball: dict[int, BattedBallRow] | FetchFailure | None = None,
    ) -> None:
        self._batter_arsenal = batter_arsenal
        self._pitcher_arsenal = pitcher_arsenal
        self._expected = expected
        self._sprint = sprint
        self._squared = squared
        self._pitcher_expected = pitcher_expected
        self._pitcher_statcast = pitcher_statcast
        self._statcast = statcast
        self._batted_ball = batted_ball

    def fetch_batted_ball(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, BattedBallRow] | FetchFailure:
        if self._batted_ball is not None:
            return self._batted_ball
        return {}

    def fetch_pitch_arsenal(
        self, *, kind: str, year: int
    ) -> tuple[PitchArsenalRow, ...] | FetchFailure:
        return self._batter_arsenal if kind == "batter" else self._pitcher_arsenal

    def fetch_statcast_batters(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, StatcastBatterRow] | FetchFailure:
        if self._statcast is not None:
            return self._statcast
        return {BATTER_ID: _statcast_row(BATTER_ID)}

    def fetch_bat_tracking(
        self, *, year: int, minimum: int = 0, start: str = "", end: str = ""
    ) -> tuple[BatTrackingRow, ...]:
        return (_tracking_row(BATTER_ID),)

    def fetch_expected_stats(self, *, year: int) -> dict[int, ExpectedStatsRow] | FetchFailure:
        if self._expected is not None:
            return self._expected
        return {}

    def fetch_sprint_speed(self, *, year: int) -> dict[int, SprintSpeedRow] | FetchFailure:
        if self._sprint is not None:
            return self._sprint
        return {}

    def fetch_squared_up(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, SquaredUpRow] | FetchFailure:
        if self._squared is not None:
            return self._squared
        return {}

    def fetch_pitcher_expected_stats(
        self, *, year: int
    ) -> dict[int, ExpectedStatsRow] | FetchFailure:
        if self._pitcher_expected is not None:
            return self._pitcher_expected
        return {}

    def fetch_statcast_pitchers(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, StatcastPitcherRow] | FetchFailure:
        if self._pitcher_statcast is not None:
            return self._pitcher_statcast
        return {}


def _park_factors() -> dict[int, dict[Handedness, ParkFactor]]:
    return {
        15: {
            Handedness.LEFT: ParkFactor(
                factor=Decimal("112"), handedness=Handedness.LEFT, plate_appearances=30000
            ),
            Handedness.RIGHT: ParkFactor(
                factor=Decimal("98"), handedness=Handedness.RIGHT, plate_appearances=30000
            ),
        }
    }


def _events_by_day() -> tuple[PitchEvent, ...]:
    return _recent_events()


def _build(api: object, savant: object, events: object = None) -> object:
    all_events = _recent_events() if events is None else events
    if isinstance(all_events, FetchFailure):

        def fetch_day(day: date) -> FetchFailure:
            return all_events
    else:

        def fetch_day(day: date) -> tuple[PitchEvent, ...]:
            return tuple(e for e in all_events if e.game_date == day.isoformat())

    return build_board(
        api=api,  # type: ignore[arg-type]
        savant=savant,  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        fetch_day_events=fetch_day,
        temperature_for=lambda venue: Decimal("78"),
        park_factors=_park_factors(),
    )


def test_happy_path_grades_every_lineup_batter() -> None:
    savant = _FakeSavant(
        batter_arsenal=(_arsenal_row(BATTER_ID, "FF", "0.5", "0.400", "0.15", "0.15"),),
        pitcher_arsenal=(_arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),),
    )
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    assert board.official_date == "2026-08-20"
    assert len(board.games) == 1
    game = board.games[0]
    assert game.venue_name == "Chase Field"
    assert game.home_pitcher is not None and game.home_pitcher.throws == "R"
    assert game.away_pitcher is None
    batter = game.away_batters[0]
    assert batter.player_id == BATTER_ID
    assert not batter.lineup_is_estimate
    assert isinstance(batter.result, EvaluatedGradeResult)
    assert Decimal(0) <= batter.result.total_score <= Decimal(12)
    scored = {score.component_id for score in batter.result.component_scores}
    assert ComponentId.EXIT_VELOCITY in scored


def test_a_slate_level_failure_is_the_only_fatal_one() -> None:
    class _DownApi(_FakeApi):
        def fetch_slate(self, date_mmddyyyy: str) -> FetchFailure:
            return FetchFailure("slate: HTTP 503")

    failure = _build(_DownApi(), _FakeSavant())
    assert isinstance(failure, FetchFailure)


def test_unposted_lineups_fall_back_to_estimates_and_are_labelled() -> None:
    savant = _FakeSavant(
        batter_arsenal=(
            _arsenal_row(BATTER_ID, "FF", "0.5", "0.400", "0.15", "0.15"),
            _arsenal_row(BATTER_ID, "SL", "0.3", "0.350", "0.15", "0.15"),
        ),
    )
    board = _build(_FakeApi(orders=BattingOrders(game_pk=777001, home=(), away=())), savant)
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    assert game.home_batters[0].lineup_is_estimate
    assert game.home_batters[0].player_id == BATTER_ID


def test_a_switch_hitter_without_a_probable_gets_named_absences() -> None:
    game = _game()
    object.__setattr__(game, "home_probable", None)

    class _NoProbableApi(_FakeApi):
        def fetch_slate(self, date_mmddyyyy: str) -> Slate:
            return Slate(official_date="2026-08-20", games=(game,))

    hitting = {BATTER_ID: _season_hitting(BATTER_ID, bats="S")}
    board = _build(_NoProbableApi(hitting=hitting), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert isinstance(batter.result, EvaluatedGradeResult)
    missing = {obs.component_id: obs.missing_reason for obs in batter.result.missing_observations}
    assert missing[ComponentId.PITCH_MIX_PRESSURE] is MissingReason.EXPECTED_PITCHER_UNKNOWN
    assert missing[ComponentId.PARK] is MissingReason.EXPECTED_PITCHER_UNKNOWN


def test_an_arsenal_board_outage_degrades_matchup_components_only() -> None:
    savant = _FakeSavant(
        batter_arsenal=FetchFailure("batter arsenal board: HTTP 503"),
        pitcher_arsenal=FetchFailure("pitcher arsenal board: HTTP 503"),
    )
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert isinstance(batter.result, EvaluatedGradeResult)
    missing = {obs.component_id: obs.missing_reason for obs in batter.result.missing_observations}
    assert missing[ComponentId.PITCH_MIX_PRESSURE] is MissingReason.SOURCE_UNAVAILABLE
    assert missing[ComponentId.PUT_AWAY_PITCH_EXPLOITATION] is MissingReason.SOURCE_UNAVAILABLE
    assert ComponentId.EXIT_VELOCITY not in missing
    assert board.diagnostics


def test_a_full_events_outage_marks_form_components_unavailable() -> None:
    board = _build(_FakeApi(), _FakeSavant(), events=FetchFailure("pitch-events: HTTP 503"))
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    missing = {obs.component_id: obs.missing_reason for obs in batter.result.missing_observations}
    assert missing[ComponentId.SWEET_SPOT_PCT] is MissingReason.SOURCE_UNAVAILABLE
    assert missing[ComponentId.PULL_PCT_AIR_BALLS] is MissingReason.SOURCE_UNAVAILABLE


def test_below_floor_samples_still_score_with_the_advisory_status() -> None:
    board = _build(_FakeApi(), _FakeSavant(), events=_recent_events()[:3])
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert isinstance(batter.result, EvaluatedGradeResult)
    present = {obs.component_id: obs for obs in batter.result.present_observations}
    sweet_spot = present[ComponentId.SWEET_SPOT_PCT]
    assert sweet_spot.sample_count == 3
    assert sweet_spot.sample_status is SampleStatus.INSUFFICIENT
    score = next(
        s for s in batter.result.component_scores if s.component_id is ComponentId.SWEET_SPOT_PCT
    )
    assert score.points_awarded >= 0  # scored, not zeroed by absence


def _open_air_game() -> ScheduledGame:
    import dataclasses

    return dataclasses.replace(
        _game(),
        game_pk=777002,
        venue_id=19,
        venue_name="Coors Field",
        home_team="Colorado Rockies",
    )


class _OpenAirApi(_FakeApi):
    def fetch_slate(self, date_mmddyyyy: str) -> Slate:
        return Slate(official_date="2026-08-20", games=(_open_air_game(),))


def _build_with_wind(api: object, wind: object) -> object:
    def fetch_day(day: date) -> tuple[PitchEvent, ...]:
        return tuple(e for e in _recent_events() if e.game_date == day.isoformat())

    return build_board(
        api=api,  # type: ignore[arg-type]
        savant=_FakeSavant(),  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        fetch_day_events=fetch_day,
        temperature_for=lambda venue: Decimal("78"),
        park_factors=_park_factors(),
        wind_for=wind,  # type: ignore[arg-type]
    )


def test_wind_reaches_an_open_air_game_card() -> None:
    board = _build_with_wind(_OpenAirApi(), lambda venue: (Decimal("9"), "WSW"))
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    assert game.venue_name == "Coors Field"
    assert game.wind_speed_mph == Decimal("9")
    assert game.wind_direction == "WSW"


def test_a_roofed_game_carries_no_wind() -> None:
    """Chase Field is a retractable roof: with no roof-state source in v1 the
    wind reading never applies (D-073), so the card carries no wind."""
    board = _build_with_wind(_FakeApi(), lambda venue: (Decimal("9"), "WSW"))
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    assert game.venue_name == "Chase Field"
    assert game.wind_speed_mph is None
    assert game.wind_direction is None


def test_open_air_card_carries_the_park_axis_and_parsed_wind() -> None:
    """SP-4 (D-119): Coors Field's measured home-to-CF axis (5 degrees) and
    the compass reading parsed to degrees true ride the game card, so the
    view never re-derives either."""
    board = _build_with_wind(_OpenAirApi(), lambda venue: (Decimal("9"), "WSW"))
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    assert game.park_orientation_degrees == Decimal("5")
    assert game.wind_from_degrees == Decimal("247.5")


def test_open_air_card_carries_the_venue_slug() -> None:
    """D-122: the park reference's venue slug rides the card so the
    conditions surface joins the pinned wind-receptiveness snapshot by it.
    The Coors fixture joins, so the slug is present; an unjoined venue
    would carry None and the receptiveness cell would read as absent."""
    board = _build_with_wind(_OpenAirApi(), lambda venue: (Decimal("9"), "WSW"))
    assert not isinstance(board, FetchFailure)
    assert board.games[0].venue_id == "coors-field"


def _pitching_log_entry(
    date_text: str, pitches: int, *, started: bool = True, game_pk: int = 1
) -> PitchingLogEntry:
    return PitchingLogEntry(date=date_text, game_pk=game_pk, started=started, pitches=pitches)


def test_workload_flags_a_heavy_last_start_as_a_raw_fact() -> None:
    """SP-3 (D-123): v2.2's firing line — a last start at 100+ pitches is
    the workload flag. Newest first, days counted to the slate date."""
    workload = _starter_workload(
        (
            _pitching_log_entry("2026-08-06", 92, game_pk=1),
            _pitching_log_entry("2026-08-18", 104, game_pk=3),
            _pitching_log_entry("2026-08-12", 88, game_pk=2),
        ),
        date(2026, 8, 22),
    )
    assert workload is not None
    assert workload.last_start_date == "2026-08-18"
    assert workload.last_start_pitches == 104
    assert workload.days_since_last_start == 4
    assert workload.last_starts == (104, 88, 92)
    assert workload.starts_in_window == 3
    assert workload.workload_flag
    assert not workload.thin_sample


def test_workload_skips_relief_outings_and_names_a_thin_window() -> None:
    """A relief outing is not a start, and a window of at most two starts
    is the thin sample the hand-split caption names (v2.2)."""
    workload = _starter_workload(
        (
            _pitching_log_entry("2026-08-20", 12, started=False, game_pk=3),
            _pitching_log_entry("2026-08-13", 88, game_pk=2),
            _pitching_log_entry("2026-08-06", 92, game_pk=1),
        ),
        date(2026, 8, 22),
    )
    assert workload is not None
    assert workload.last_start_date == "2026-08-13"
    assert workload.last_starts == (88, 92)
    assert workload.starts_in_window == 2
    assert not workload.workload_flag
    assert workload.thin_sample


def test_workload_without_a_start_is_an_absence() -> None:
    assert _starter_workload((), date(2026, 8, 22)) is None
    relief_only = (_pitching_log_entry("2026-08-20", 15, started=False),)
    assert _starter_workload(relief_only, date(2026, 8, 22)) is None


def _drift_event(pitch_type: str, description: str) -> PitchEvent:
    return PitchEvent(
        game_pk=777000,
        game_date="2026-08-19",
        batter_id=BATTER_ID,
        pitcher_id=PITCHER_ID,
        batter_side="L",
        pitcher_throws="R",
        pitch_type=pitch_type,
        event="",
        description=description,
        bb_type="",
        launch_speed=None,
        launch_angle=None,
        launch_speed_angle=None,
        hc_x=None,
        hc_y=None,
        estimated_woba=None,
        woba_value=None,
        woba_denom=None,
    )


def test_stuff_drift_reads_the_primary_pitch_against_the_window() -> None:
    """SP-3 (D-123): the board's top-usage pitch is the primary; its season
    shares face the same shares computed from the window's kept events."""
    rows = (
        _arsenal_row(PITCHER_ID, "FF", "0.50", "0.300", "0.25", "0.20"),
        _arsenal_row(PITCHER_ID, "SL", "0.30", "0.280", "0.30", "0.22"),
    )
    events = (
        _drift_event("FF", "swinging_strike"),
        _drift_event("FF", "foul"),
        _drift_event("FF", "hit_into_play"),
        _drift_event("SL", "ball"),
    )
    drift = _stuff_drift(rows, events)
    assert drift is not None
    assert drift.pitch_type == "FF"
    assert drift.pitches_in_window == 3
    assert drift.usage_season == Decimal("0.50")
    assert drift.usage_window == Decimal("0.75")
    assert drift.whiff_season == Decimal("0.25")
    assert drift.whiff_window == Decimal(1) / Decimal(3)


def test_stuff_drift_names_empty_denominators_and_honest_zeros() -> None:
    rows = (_arsenal_row(PITCHER_ID, "FF", "0.50", "0.300", "0.25", "0.20"),)
    # Nobody swung at the primary pitch in the window: the whiff names its
    # absence; the usage is a full honest share.
    drift = _stuff_drift(rows, (_drift_event("FF", "called_strike"),))
    assert drift is not None
    assert drift.pitches_in_window == 1
    assert drift.usage_window == Decimal(1)
    assert drift.whiff_window is None
    # The primary pitch never thrown in the window is an honest zero usage.
    drift = _stuff_drift(rows, (_drift_event("SL", "ball"),))
    assert drift is not None
    assert drift.usage_window == Decimal(0)
    assert drift.whiff_window is None
    # No typed events at all: the usage names its absence.
    empty = _stuff_drift(rows, ())
    assert empty is not None
    assert empty.pitches_in_window == 0
    assert empty.usage_window is None
    # No board rows: no drift line at all.
    assert _stuff_drift((), (_drift_event("FF", "ball"),)) is None


def test_the_card_carries_the_workload_and_drift_facts() -> None:
    """SP-3 (D-123): the pitching game log and the window events land on
    the pitcher card computed — the view only formats (GMF-008)."""
    board = _build(
        _FakeApi(
            pitching_logs={
                PITCHER_ID: (
                    _pitching_log_entry("2026-08-18", 101, game_pk=3),
                    _pitching_log_entry("2026-08-12", 88, game_pk=2),
                )
            }
        ),
        _FakeSavant(
            pitcher_arsenal=(_arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),)
        ),
    )
    assert not isinstance(board, FetchFailure)
    pitcher = board.games[0].home_pitcher
    assert pitcher is not None
    assert pitcher.workload is not None
    assert pitcher.workload.last_start_pitches == 101
    assert pitcher.workload.workload_flag
    assert pitcher.workload.thin_sample  # two starts in the window
    assert pitcher.stuff_drift is not None
    assert pitcher.stuff_drift.pitch_type == "FF"


def test_roofed_card_carries_neither_axis_nor_wind_bearing() -> None:
    """A roofed venue's axis is a designed absence (D-073/D-119): no wind
    reaches the field, so no bearing may resolve."""
    board = _build_with_wind(_FakeApi(), lambda venue: (Decimal("9"), "WSW"))
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    assert game.park_orientation_degrees is None
    assert game.wind_from_degrees is None


def test_an_unparseable_compass_reading_degrades_to_none() -> None:
    """A direction text outside the sixteen-point compass is an honest
    absence — the wind tags stay silent rather than resolve against a
    guessed bearing."""
    board = _build_with_wind(_OpenAirApi(), lambda venue: (Decimal("9"), "Variable"))
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    assert game.wind_speed_mph == Decimal("9")
    assert game.wind_from_degrees is None


def test_recent_events_cover_the_newest_games_with_every_pitch() -> None:
    """D-086: the log's source rows are the newest seven games' events, all
    pitches kept (the mix needs full counts), newest game first."""
    import dataclasses

    from greenmachine.live.pipeline import _recent_window_events

    base = _recent_events()[0]
    events = tuple(
        dataclasses.replace(base, game_date=day)
        for day in ("2026-08-17", "2026-08-19", "2026-08-19")
    )
    rows = _recent_window_events(events)
    assert [event.game_date for event in rows] == ["2026-08-19", "2026-08-19", "2026-08-17"]


def test_recent_events_cap_drops_older_games() -> None:
    import dataclasses

    from greenmachine.live.pipeline import _recent_window_events

    base = _recent_events()[0]
    days = [f"2026-08-{day:02d}" for day in range(5, 20)]  # fifteen game days
    events = tuple(dataclasses.replace(base, game_date=day) for day in days)
    rows = _recent_window_events(events)
    assert {event.game_date for event in rows} == set(days[-7:])


def _window_event(**overrides: object) -> PitchEvent:
    import dataclasses

    base = _recent_events()[0]
    return dataclasses.replace(base, **overrides)  # type: ignore[arg-type]


def test_pitch_lines_derive_every_rate_from_the_given_scope() -> None:
    """§GMF-008: usage divides by the scope's pitches, AVG/SLG by its at-bats,
    barrel and hard-hit by its batted balls, whiff by its swings, xwOBA by its
    plate appearances — never by a denominator from outside the scope."""
    from greenmachine.live.pipeline import _pitch_lines

    events = (
        _window_event(
            pitch_type="FF",
            event="home_run",
            launch_speed=Decimal("110"),
            launch_speed_angle=6,
            estimated_woba=Decimal("2.0"),
            description="hit_into_play",
        ),
        _window_event(
            pitch_type="FF",
            event="field_out",
            launch_speed=Decimal("90"),
            launch_speed_angle=3,
            estimated_woba=Decimal("0.2"),
            description="hit_into_play",
        ),
        _window_event(
            pitch_type="FF",
            event="strikeout",
            launch_speed=None,
            launch_angle=None,
            launch_speed_angle=None,
            bb_type="",
            estimated_woba=None,
            description="swinging_strike",
        ),
        _window_event(
            pitch_type="SL",
            event="",
            launch_speed=None,
            launch_angle=None,
            launch_speed_angle=None,
            bb_type="",
            estimated_woba=None,
            description="called_strike",
        ),
    )
    lines = {line.pitch_type: line for line in _pitch_lines(events)}
    fastball = lines["FF"]
    assert fastball.pitch_name == "4-Seam Fastball"
    assert fastball.pitches == 3
    assert fastball.usage_share == Decimal(3) / Decimal(4)
    assert fastball.plate_appearances == 3
    assert fastball.batting_average == Decimal(1) / Decimal(3)
    assert fastball.slugging == Decimal(4) / Decimal(3)
    assert fastball.iso is not None
    assert fastball.iso.quantize(Decimal("0.001")) == Decimal("1.000")
    assert fastball.home_runs == 1
    assert fastball.barrel_share == Decimal(1) / Decimal(2)
    assert fastball.hard_hit_share == Decimal(1) / Decimal(2)
    assert fastball.expected_woba == Decimal("2.2") / Decimal(2)
    assert fastball.whiff_share == Decimal(1) / Decimal(3)
    # D-124: the per-pitch mean launch angle reads the pitches with a
    # measured angle — the same measured-event base EV reads.
    assert fastball.mean_launch_angle == Decimal("20")
    slider = lines["SL"]
    assert slider.usage_share == Decimal(1) / Decimal(4)
    # A pitch thrown but never put in play carries named absences, not zeros.
    assert slider.plate_appearances == 0
    assert slider.batting_average is None
    assert slider.barrel_share is None
    assert slider.whiff_share is None
    assert slider.mean_launch_angle is None


def test_pitch_lines_sort_by_usage_and_empty_scope_is_absent() -> None:
    from greenmachine.live.pipeline import _pitch_lines

    assert _pitch_lines(()) == ()
    events = tuple(
        _window_event(pitch_type="FF" if index else "CH", event="") for index in range(3)
    )
    assert [line.pitch_type for line in _pitch_lines(events)] == ["FF", "CH"]


def test_pitch_lines_carry_the_season_breakup_counts_and_air_reads() -> None:
    """D-129 (PO): at-bats and hits beside the rates, the raw barrel count,
    the pull/oppo shares of measurable air (the form section's exact
    convention), and the per-side expected ISO off the per-event expected
    SLG/BA — every figure off the same scope of events."""
    from greenmachine.live.pipeline import _pitch_lines

    events = (
        # a pulled air-ball barrel (spray +27 degrees for a right-hander)
        _window_event(
            pitch_type="FF",
            event="home_run",
            batter_side="R",
            bb_type="fly_ball",
            launch_speed=Decimal("108"),
            launch_angle=Decimal("27"),
            launch_speed_angle=6,
            hc_x=Decimal("150"),
            hc_y=Decimal("150"),
            estimated_slg=Decimal("1.9"),
            estimated_ba=Decimal("0.8"),
        ),
        # an opposite-field air out (spray -27.6 degrees), not a barrel
        _window_event(
            pitch_type="FF",
            event="field_out",
            batter_side="R",
            bb_type="fly_ball",
            launch_speed=Decimal("95"),
            launch_angle=Decimal("30"),
            launch_speed_angle=3,
            hc_x=Decimal("100"),
            hc_y=Decimal("150"),
            estimated_slg=Decimal("0.3"),
            estimated_ba=Decimal("0.2"),
        ),
        # a ground ball — never air, however it is sprayed
        _window_event(
            pitch_type="FF",
            event="field_out",
            batter_side="R",
            bb_type="ground_ball",
            launch_speed=Decimal("88"),
            launch_angle=Decimal("4"),
            launch_speed_angle=2,
            hc_x=Decimal("150"),
            hc_y=Decimal("150"),
            estimated_slg=None,
            estimated_ba=None,
        ),
        # a walk — a plate appearance, never an at-bat
        _window_event(
            pitch_type="FF",
            event="walk",
            batter_side="R",
            bb_type="",
            launch_speed=None,
            launch_angle=None,
            launch_speed_angle=None,
            hc_x=None,
            hc_y=None,
            estimated_slg=None,
            estimated_ba=None,
        ),
    )
    (fastball,) = _pitch_lines(events)
    assert fastball.plate_appearances == 4
    assert fastball.at_bats == 3
    assert fastball.hits == 1
    assert fastball.batting_average == Decimal(1) / Decimal(3)
    assert fastball.barrel_count == 1
    assert fastball.barrel_share == Decimal(1) / Decimal(3)
    assert fastball.pull_air_share == Decimal(1) / Decimal(2)
    assert fastball.oppo_air_share == Decimal(1) / Decimal(2)
    assert fastball.expected_iso is not None
    assert fastball.expected_iso.quantize(Decimal("0.001")) == Decimal("0.600")


def test_season_breakup_lines_scope_both_halves_to_the_matchup_hands() -> None:
    """D-129 (PO): the default rebases every metric to the matchup's hands —
    his pitches to the batter's side, the batter's pitches seen from the
    starter's hand — and the unfiltered position rebases to all hands over
    the identical records."""
    from greenmachine.live.pipeline import season_breakup_lines

    pitcher_events = (
        _window_event(pitch_type="FF", batter_side="L"),
        _window_event(pitch_type="FF", batter_side="L"),
        _window_event(pitch_type="SL", batter_side="R"),
        _window_event(pitch_type="SL", batter_side="L"),
    )
    batter_events = (
        _window_event(pitch_type="FF", pitcher_throws="L"),
        _window_event(pitch_type="FF", pitcher_throws="R"),
        _window_event(pitch_type="FF", pitcher_throws="R"),
        _window_event(pitch_type="CH", pitcher_throws="R"),
    )
    pitcher_lines, batter_lines = season_breakup_lines(
        pitcher_events, batter_events, batter_side="L", pitcher_throws="L", hand_filter=True
    )
    assert {line.pitch_type for line in pitcher_lines} == {"FF", "SL"}
    fastball = next(line for line in pitcher_lines if line.pitch_type == "FF")
    assert fastball.pitches == 2
    assert fastball.usage_share == Decimal(2) / Decimal(3)  # rebased to the LHB scope
    assert set(batter_lines) == {"FF"}  # only the pitches he has seen from a lefty
    assert batter_lines["FF"].pitches == 1
    pitcher_all, batter_all = season_breakup_lines(
        pitcher_events, batter_events, batter_side="L", pitcher_throws="L", hand_filter=False
    )
    assert {line.pitch_type for line in pitcher_all} == {"FF", "SL"}
    assert set(batter_all) == {"FF", "CH"}
    assert batter_all["FF"].pitches == 3


def test_pitcher_season_lines_read_the_season_board() -> None:
    """D-087: the Arsenal table's figures are the season arsenal board's own,
    ISO derived pipeline-side, sorted by usage; the board publishes no home-run
    count, so that cell is None rather than an invented zero."""
    savant = _FakeSavant(
        pitcher_arsenal=(
            _arsenal_row(PITCHER_ID, "SL", "0.25", "0.280", "0.22", "0.18"),
            _arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),
        ),
    )
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    pitcher = board.games[0].home_pitcher
    assert pitcher is not None
    assert pitcher.season_lines_year == SLATE_DATE.year
    assert [line.pitch_type for line in pitcher.season_lines] == ["FF", "SL"]
    fastball = pitcher.season_lines[0]
    assert fastball.iso == Decimal("0.400") - Decimal("0.250")
    assert fastball.woba == Decimal("0.300")
    assert fastball.strikeout_share == Decimal("0.2")
    assert fastball.expected_woba == Decimal("0.300")
    assert fastball.home_runs is None
    assert fastball.barrel_share is None


def test_pitcher_without_a_current_record_falls_back_to_last_season() -> None:
    """D-087: a probable with no current-season arsenal row reads his
    prior-year board, labelled with that year; the fallback fetches once and
    only for the pitchers who need it."""

    class _FallbackSavant(_FakeSavant):
        def fetch_pitch_arsenal(
            self, *, kind: str, year: int
        ) -> tuple[PitchArsenalRow, ...] | FetchFailure:
            if kind == "pitcher" and year == SLATE_DATE.year:
                return ()  # no current-season record at all
            if kind == "pitcher":
                return (_arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),)
            return (_arsenal_row(BATTER_ID, "FF", "0.5", "0.400", "0.15", "0.15"),)

    board = _build(_FakeApi(), _FallbackSavant())
    assert not isinstance(board, FetchFailure)
    pitcher = board.games[0].home_pitcher
    assert pitcher is not None
    assert [line.pitch_type for line in pitcher.season_lines] == ["FF"]
    assert pitcher.season_lines_year == SLATE_DATE.year - 1


def test_pitcher_side_sets_read_the_window() -> None:
    """D-087: the side filter's pitch-type sets come from the recent pitch
    record — the only per-side read on the board — one set per batter side."""
    events = (
        _window_event(pitch_type="FF", batter_side="L"),
        _window_event(pitch_type="SL", batter_side="R", batter_id=909),
    )
    board = _build(_FakeApi(), _FakeSavant(), events=events)
    assert not isinstance(board, FetchFailure)
    pitcher = board.games[0].home_pitcher
    assert pitcher is not None
    assert pitcher.pitches_vs_left == frozenset({"FF"})
    assert pitcher.pitches_vs_right == frozenset({"SL"})


def test_pitcher_side_usage_is_each_sides_share_of_the_window() -> None:
    """D-102: usage vs a hitter hand is each pitch type's share of his
    pitches to that side in the window record — the per-side basis the
    arsenal toggle switches to. A side with no pitches maps to nothing,
    never an invented share."""
    events = (
        _window_event(pitch_type="FF", batter_side="L"),
        _window_event(pitch_type="FF", batter_side="L"),
        _window_event(pitch_type="SL", batter_side="L"),
        _window_event(pitch_type="FF", batter_side="R", batter_id=909),
    )
    board = _build(_FakeApi(), _FakeSavant(), events=events)
    assert not isinstance(board, FetchFailure)
    pitcher = board.games[0].home_pitcher
    assert pitcher is not None
    assert pitcher.usage_vs_left == {"FF": Decimal(2) / Decimal(3), "SL": Decimal(1) / Decimal(3)}
    assert pitcher.usage_vs_right == {"FF": Decimal(1)}


def test_batter_matchup_lines_are_side_scoped_over_each_window() -> None:
    """D-106: the arsenal breakup's batter half is precomputed at each reach
    in MATCHUP_LINE_WINDOWS_DAYS — one line per pitch in the starter's season
    arsenal, in his usage order, carrying HIS usage share; the batter's own
    figures keep the window's scope. Same-side pitching and pitches older
    than the reach never enter a denominator, a pitch the batter has not
    seen keeps zeroed counts and empty rates, and with no probable named
    there is no scope and the card carries no lines."""
    events = (
        _window_event(pitch_type="FF", pitcher_throws="R"),
        _window_event(pitch_type="FF", pitcher_throws="R"),
        _window_event(pitch_type="SL", pitcher_throws="L"),  # wrong side
        _window_event(
            pitch_type="CU", pitcher_throws="R", game_date="2026-07-10"
        ),  # outside every reach
    )
    savant = _FakeSavant(
        pitcher_arsenal=(
            _arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),
            _arsenal_row(PITCHER_ID, "SL", "0.25", "0.280", "0.22", "0.18"),
        ),
    )
    board = _build(_FakeApi(), savant, events=events)
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    # The away lineup faces the home probable, a right-hander.
    away = game.away_batters[0]
    assert set(away.matchup_lines_by_window) == {7, 14, 21, 28, 30}
    lines = away.matchup_lines_by_window[30]
    assert [line.pitch_type for line in lines] == ["FF", "SL"]
    fastball = lines[0]
    assert fastball.pitches == 2
    # Usage is the starter's season share, never the batter's seen share.
    assert fastball.usage_share == Decimal("0.55")
    sweeper = lines[1]
    assert sweeper.pitches == 0
    assert sweeper.usage_share == Decimal("0.25")
    assert sweeper.batting_average is None
    # Each shorter reach precomputes the same join.
    assert [line.pitch_type for line in away.matchup_lines_by_window[7]] == ["FF", "SL"]
    # The home lineup has no named opposing starter: no scope, no lines.
    assert game.home_batters[0].matchup_lines_by_window == {}


def test_mix_line_counts_only_the_qualifying_mix_pitches() -> None:
    """D-079: the grid line reads the batter's window events against the
    starter's qualifying (>=14% usage) mix pitches — a fringe pitch the
    starter barely throws never enters a denominator. With no probable
    named there is no scope and no line (D-081). D-128 (PO): with no
    arsenal board at either year the mix falls back to the two-month
    event record, labelled."""
    pitcher_events = tuple(
        _window_event(batter_id=555, pitcher_id=PITCHER_ID, pitch_type="FF") for _ in range(20)
    ) + tuple(
        _window_event(batter_id=555, pitcher_id=PITCHER_ID, pitch_type="SL") for _ in range(2)
    )
    batter_events = tuple(
        _window_event(pitch_type="FF", event="single", pitcher_id=999) for _ in range(4)
    ) + tuple(_window_event(pitch_type="SL", event="double", pitcher_id=999) for _ in range(4))
    board = _build(_FakeApi(), _FakeSavant(), events=pitcher_events + batter_events)
    assert not isinstance(board, FetchFailure)
    away = board.games[0].away_batters[0]
    assert away.mix_label == "last 60 days"
    line = away.mix_line
    assert line is not None
    assert line.pitches == 4
    assert line.at_bats == 4
    assert line.hits == 4  # the four SL events are outside the qualifying mix
    assert board.games[0].home_batters[0].mix_line is None


def test_the_mix_reads_the_season_board_first() -> None:
    """D-128 (PO): the mix scope is the starter's whole season off the
    arsenal board, labelled "season" — the two-month record and last
    season's board are fallbacks now. The board's usage decides the
    qualifying mix even when the event record disagrees."""
    # The record is all sliders; the board says the curveball is a real
    # pitch (20% >= the 14% qualifying share) — so the batter's curveball
    # hits count against the mix.
    pitcher_events = tuple(
        _window_event(batter_id=555, pitcher_id=PITCHER_ID, pitch_type="SL") for _ in range(20)
    )
    batter_events = tuple(
        _window_event(pitch_type="CB", event="single", pitcher_id=999) for _ in range(4)
    )
    savant = _FakeSavant(
        pitcher_arsenal=(
            _arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),
            _arsenal_row(PITCHER_ID, "CB", "0.20", "0.280", "0.22", "0.18"),
        ),
    )
    board = _build(_FakeApi(), savant, events=pitcher_events + batter_events)
    assert not isinstance(board, FetchFailure)
    away = board.games[0].away_batters[0]
    assert away.mix_label == "season"
    line = away.mix_line
    assert line is not None
    assert line.at_bats == 4  # the board's curveball qualifies the scope


def test_the_mix_falls_back_to_the_two_month_record_without_a_board() -> None:
    """D-128 (PO): with no arsenal board at either year the mix reads the
    two-month event record, labelled. D-081's separate L45 reach is
    subsumed — the fetch spans sixty-one days on every build, so a pitch
    thrown forty-five days back still makes the mix and no second fetch
    ever fires."""
    old_starter_events = (
        _window_event(
            batter_id=555, pitcher_id=PITCHER_ID, pitch_type="FF", game_date="2026-07-06"
        ),
    )
    batter_events = (_window_event(pitch_type="FF", event="single", pitcher_id=999),)
    all_events = old_starter_events + batter_events
    fetched: list[date] = []

    def fetch_day(day: date) -> tuple[PitchEvent, ...]:
        fetched.append(day)
        return tuple(e for e in all_events if e.game_date == day.isoformat())

    board = build_board(
        api=_FakeApi(),  # type: ignore[arg-type]
        savant=_FakeSavant(),  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        fetch_day_events=fetch_day,
        temperature_for=lambda venue: Decimal("78"),
        park_factors=_park_factors(),
    )
    assert not isinstance(board, FetchFailure)
    away = board.games[0].away_batters[0]
    assert away.mix_label == "last 60 days"
    assert min(fetched) == date(2026, 6, 21)  # one 61-day record, no reach
    line = away.mix_line
    assert line is not None
    assert line.at_bats == 1
    # The same forty-five-day-old event feeds the starter's recent line.
    starter = board.games[0].home_pitcher
    assert starter is not None and starter.recent_overall is not None
    assert starter.recent_overall.plate_appearances == 1


def test_the_batter_window_parameter_rewindows_the_grid_and_reaches() -> None:
    """D-128 (PO): the Matchups tab's timeframe selector passes its own
    batter window — the grid scope and the precomputed dialog reaches
    follow it, the robbed count keeps its own L7 basis on both lines, and
    the fetch still spans the two-month pitcher record."""
    batter_events = (
        _window_event(
            pitch_type="FF", event="single", pitcher_id=999, game_date="2026-08-15"
        ),  # five days back — inside a 14-day window
        _window_event(
            pitch_type="FF", event="single", pitcher_id=999, game_date="2026-08-01"
        ),  # nineteen days back — outside it
        _window_event(
            pitch_type="FF",
            event="field_out",
            pitcher_id=999,
            game_date="2026-08-16",
            hit_distance=Decimal("380"),
            launch_speed_angle=3,
        ),  # robbed-shaped, six days back — inside the L7 basis
    )
    pitcher_events = tuple(
        _window_event(batter_id=555, pitcher_id=PITCHER_ID, pitch_type="FF") for _ in range(20)
    )
    all_events = batter_events + pitcher_events
    fetched: list[date] = []

    def fetch_day(day: date) -> tuple[PitchEvent, ...]:
        fetched.append(day)
        return tuple(e for e in all_events if e.game_date == day.isoformat())

    savant = _FakeSavant(
        pitcher_arsenal=(_arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),),
    )
    board = build_board(
        api=_FakeApi(),  # type: ignore[arg-type]
        savant=savant,  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        batter_window_days=14,
        fetch_day_events=fetch_day,
        temperature_for=lambda venue: Decimal("78"),
        park_factors=_park_factors(),
    )
    assert not isinstance(board, FetchFailure)
    away = board.games[0].away_batters[0]
    line = away.mix_line
    assert line is not None
    assert line.at_bats == 2  # the 14-day scope: the single and the out
    assert line.robbed_hr_count == 1  # the L7 basis inside the window
    assert set(away.matchup_lines_by_window) == {7, 14}
    season_line = away.season_line
    assert season_line is not None
    assert season_line.robbed_hr_count == 1  # D-128 (PO): shown on both views
    assert min(fetched) == date(2026, 6, 21)  # the pitcher reach still governs


def test_the_batter_window_cannot_undercut_the_robbed_basis() -> None:
    """D-128: the robbed count reads window_cutoffs[7], so a batter window
    under seven days is a programmer error named loudly, never a KeyError."""
    import pytest

    with pytest.raises(ValueError, match="batter window"):
        build_board(
            api=_FakeApi(),  # type: ignore[arg-type]
            savant=_FakeSavant(),  # type: ignore[arg-type]
            slate_date=SLATE_DATE,
            as_of=AS_OF,
            config=CONFIG,
            batter_window_days=5,
            fetch_day_events=lambda day: (),
            temperature_for=lambda venue: Decimal("78"),
            park_factors=_park_factors(),
        )


def test_straight_air_share_reads_the_fifteen_degree_band() -> None:
    """D-128 (PO): the straight-away profile is the air balls within
    fifteen degrees of dead center over the identical measurable-air
    denominator. Pull and oppo keep the ratified signed convention, so
    they partition the set while straight overlaps a near-center ball's
    signed side — one denominator, not a partition."""
    from greenmachine.live.pipeline import _batter_grid_line

    # The fixture batter is a lefty: spray < 0 is his pull side.
    pull = _window_event(hc_x=Decimal("96.9"), hc_y=Decimal("120"))  # -20 deg
    straight = _window_event(hc_x=Decimal("125.42"), hc_y=Decimal("120"))  # dead center
    oppo = _window_event(hc_x=Decimal("153.9"), hc_y=Decimal("120"))  # +20 deg
    overlap = _window_event(
        hc_x=Decimal("111.6"), hc_y=Decimal("120")
    )  # -10 deg: pull AND straight
    line = _batter_grid_line((pull, straight, oppo, overlap), robbed_count=0)
    assert line is not None
    assert line.pull_air_share == Decimal("0.5")  # the -20 and the -10
    assert line.oppo_air_share == Decimal("0.25")
    assert line.straight_air_share == Decimal("0.5")  # dead center and the -10
    # Pull and oppo partition; straight's band crosses the signed sides.
    assert line.pull_air_share + line.oppo_air_share == Decimal("0.75")


def test_the_season_line_reads_the_published_air_profiles() -> None:
    """D-128 (PO): the season view's pull/straight/oppo are Savant's own
    published buckets off the batted-ball board, rebased pipeline-side to
    shares of the batter's air balls — published numbers, never a
    home-built derivation. No board row, no split: named absences."""
    hitting = {
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
    savant = _FakeSavant(
        batted_ball={
            BATTER_ID: BattedBallRow(
                player_id=BATTER_ID,
                batted_ball_events=300,
                air_share=Decimal("0.50"),
                pull_air_share_of_bbe=Decimal("0.16"),
                straight_air_share_of_bbe=Decimal("0.19"),
                oppo_air_share_of_bbe=Decimal("0.15"),
            )
        },
    )
    board = _build(_FakeApi(hitting=hitting), savant)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].season_line
    assert line is not None
    assert line.pull_air_share == Decimal("0.32")  # 0.16 / 0.50
    assert line.straight_air_share == Decimal("0.38")
    assert line.oppo_air_share == Decimal("0.30")
    total = line.pull_air_share + line.straight_air_share + line.oppo_air_share
    assert total == Decimal(1)  # the published buckets partition air balls

    # An empty air share publishes no split — named absences, never a
    # divide-by-zero.
    grounded = _FakeSavant(
        batted_ball={
            BATTER_ID: BattedBallRow(
                player_id=BATTER_ID,
                batted_ball_events=300,
                air_share=Decimal("0"),
                pull_air_share_of_bbe=Decimal("0"),
                straight_air_share_of_bbe=Decimal("0"),
                oppo_air_share_of_bbe=Decimal("0"),
            )
        },
    )
    board = _build(_FakeApi(hitting=hitting), grounded)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].season_line
    assert line is not None
    assert line.pull_air_share is None
    assert line.straight_air_share is None
    assert line.oppo_air_share is None


def test_mix_falls_back_to_the_season_board_when_no_window_pitches() -> None:
    """D-081: with no window pitches at either reach, the mix is the season
    board, named 'season'."""
    batter_events = (_window_event(pitch_type="FF", event="single", pitcher_id=999),)
    savant = _FakeSavant(
        pitcher_arsenal=(_arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),),
    )
    board = _build(_FakeApi(), savant, events=batter_events)
    assert not isinstance(board, FetchFailure)
    away = board.games[0].away_batters[0]
    assert away.mix_label == "season"
    line = away.mix_line
    assert line is not None
    assert line.at_bats == 1


def test_mix_falls_back_to_last_season_when_no_current_record() -> None:
    """D-081: the chain ends at last season's board when the pitcher has no
    current-season record either, named 'last season'."""

    class _FallbackSavant(_FakeSavant):
        def fetch_pitch_arsenal(
            self, *, kind: str, year: int
        ) -> tuple[PitchArsenalRow, ...] | FetchFailure:
            if kind == "pitcher" and year == SLATE_DATE.year:
                return ()
            if kind == "pitcher":
                return (_arsenal_row(PITCHER_ID, "FF", "0.55", "0.300", "0.25", "0.20"),)
            return ()

    batter_events = (_window_event(pitch_type="FF", event="single", pitcher_id=999),)
    board = _build(_FakeApi(), _FallbackSavant(), events=batter_events)
    assert not isinstance(board, FetchFailure)
    away = board.games[0].away_batters[0]
    assert away.mix_label == "last season"
    line = away.mix_line
    assert line is not None
    assert line.at_bats == 1


def test_robbed_hr_counts_375_plus_balls_that_stayed_in_the_park_over_l7() -> None:
    """PO 2026-08-24 (replacing D-090's +350 ft column): the robbed-HR
    count tallies projected-375+ ft balls that did not leave the park —
    a home run was robbed of nothing — over the last 7 days of kept
    events, a raw count and never a rate."""
    base = {
        "pitch_type": "FF",
        "launch_speed": Decimal("100"),
        "hc_y": Decimal("150"),
        "event": "fly_out",
    }
    events = (
        _window_event(bb_type="fly_ball", hit_distance=Decimal("380"), **base),  # robbed
        _window_event(bb_type="fly_ball", hit_distance=Decimal("374"), **base),  # short
        _window_event(bb_type="fly_ball", hit_distance=Decimal("390"), **base),  # robbed
        _window_event(  # 410 ft but OUT of the park: robbed of nothing
            event="home_run",
            bb_type="fly_ball",
            hit_distance=Decimal("410"),
            pitch_type="FF",
            launch_speed=Decimal("105"),
            hc_y=Decimal("150"),
        ),
        _window_event(  # 395 ft but eight-plus days old: outside the window
            bb_type="fly_ball", hit_distance=Decimal("395"), game_date="2026-08-01", **base
        ),
        _window_event(  # no measured distance: never tallied
            event="",
            launch_speed=None,
            launch_angle=None,
            launch_speed_angle=None,
            hit_distance=None,
            description="ball",
        ),
    )
    board = _build(_FakeApi(), _FakeSavant(), events=events)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].mix_line
    assert line is not None
    assert line.robbed_hr_count == 2


def test_pull_air_share_mirrors_the_form_section() -> None:
    """D-090: Pull Air % is its own metric — pulled air balls over
    measurable air balls, matching the form section's definition; distance
    plays no part."""
    pull_x, oppo_x = Decimal("100"), Decimal("150")  # L batter: spray < 0 pulls
    base = {
        "pitch_type": "FF",
        "launch_speed": Decimal("100"),
        "hc_y": Decimal("150"),
        "event": "fly_out",
    }
    events = (
        _window_event(bb_type="fly_ball", hc_x=pull_x, hit_distance=Decimal("290"), **base),
        _window_event(bb_type="fly_ball", hc_x=pull_x, hit_distance=Decimal("310"), **base),
        _window_event(bb_type="fly_ball", hc_x=oppo_x, hit_distance=Decimal("390"), **base),
        _window_event(
            **{**base, "bb_type": "fly_ball", "hc_x": None, "hc_y": None},
            hit_distance=Decimal("380"),
        ),  # unmeasurable: out of both pull-air counts
        _window_event(bb_type="ground_ball", hc_x=pull_x, hit_distance=Decimal("60"), **base),
    )
    board = _build(_FakeApi(), _FakeSavant(), events=events)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].mix_line
    assert line is not None
    # 2 pulls over 3 measurable air balls (the hc-less fly ball is out of
    # both counts); distance plays no part — the pulls are 290 and 310 ft.
    assert line.pull_air_share is not None
    assert line.pull_air_share.quantize(Decimal("0.001")) == Decimal("0.667")
    assert line.robbed_hr_count == 2  # the 390 and 380: distance only


def test_season_grid_line_composes_the_season_sources() -> None:
    """D-079's toggle target: the season line reads the hitting line
    (AVG/SLG/ISO from total bases), the statcast board (EV, barrels,
    hard-hit), and the arsenal board (PA-weighted xwOBA, pitch-weighted
    Swing-Str). The season scope has no per-event record, so the spray
    reads stay None — while the robbed count rides along on its own L7
    basis (D-128, PO)."""
    hitting = {
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
            total_bases=204,
        )
    }
    savant = _FakeSavant(
        batter_arsenal=(
            _arsenal_row(BATTER_ID, "FF", "0.5", "0.400", "0.15", "0.15"),
            _arsenal_row(BATTER_ID, "SL", "0.5", "0.300", "0.25", "0.15"),
        ),
    )
    board = _build(_FakeApi(hitting=hitting), savant)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].season_line
    assert line is not None
    assert line.at_bats == 440
    assert line.hits == 121
    assert line.home_runs == 33
    assert line.slugging is not None and line.slugging.quantize(Decimal("0.001")) == Decimal(
        "0.464"
    )
    assert line.iso is not None and line.iso.quantize(Decimal("0.001")) == Decimal("0.189")
    assert line.exit_velocity == Decimal("91.5")
    assert line.batted_balls == 300
    assert line.barrels == 30
    assert line.barrel_per_pa == Decimal("0.06")
    assert line.hard_hit_share == Decimal("0.5")
    assert line.expected_woba == Decimal("0.35")
    assert line.whiff_share == Decimal("0.20")
    # D-128 (PO): the robbed count rides the season line too — always the
    # L7 basis; the fixture's balls carry no distances, so zero robbed.
    assert line.robbed_hr_count == 0
    assert line.pull_air_share is None
    assert line.straight_air_share is None  # no season spray read
    # D-124: the season average launch angle rides the season line off the
    # Statcast board — context only, never a firing line.
    assert line.avg_launch_angle == Decimal("16.4")


def test_the_season_line_leaves_launch_angle_none_without_a_statcast_row() -> None:
    """D-124: no Statcast board row, no season LA — the surface names the
    absence, never an invented average."""
    hitting = {
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
            total_bases=204,
        )
    }
    savant = _FakeSavant(statcast={})
    board = _build(_FakeApi(hitting=hitting), savant)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].season_line
    assert line is not None
    assert line.avg_launch_angle is None


def _log_entry(date: str, home_runs: int, plate_appearances: int = 4) -> GameLogEntry:
    return GameLogEntry(
        date=date,
        game_pk=777001,
        home_runs=home_runs,
        plate_appearances=plate_appearances,
    )


def _expected_row(player_id: int) -> ExpectedStatsRow:
    return ExpectedStatsRow(
        player_id=player_id,
        plate_appearances=500,
        balls_in_play=380,
        batting_average=Decimal("0.250"),
        slugging=Decimal("0.460"),
        woba=Decimal("0.340"),
        expected_batting_average=Decimal("0.270"),
        expected_slugging=Decimal("0.500"),
        xwoba=Decimal("0.360"),
    )


def test_the_season_line_carries_the_regression_gaps() -> None:
    """D-110: xISO is est_slg - est_ba against the board's own slg - ba;
    xwOBA-wOBA reads the same board — one source, matched denominators."""
    savant = _FakeSavant(expected={BATTER_ID: _expected_row(BATTER_ID)})
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    gaps = batter.season_gaps
    assert gaps is not None
    # expected ISO .500 - .270 = .230; actual ISO .460 - .250 = .210.
    assert gaps.xiso_minus_iso == Decimal("0.020")
    assert gaps.xwoba_minus_woba == Decimal("0.020")
    assert gaps.plate_appearances == 500
    assert batter.season_line is not None
    assert batter.season_line.gaps == gaps
    # The L30 line never carries the season gaps.
    assert batter.mix_line is None or batter.mix_line.gaps is None


def test_regression_gaps_are_absent_without_a_board_row() -> None:
    board = _build(_FakeApi(), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert batter.season_gaps is None
    assert batter.season_line is not None
    assert batter.season_line.gaps is None


def test_babip_reads_the_season_counting_line() -> None:
    """D-110: (H-HR)/(AB-K-HR+SF) — 88 over 440-130-33+4 = 281."""
    hitting = {
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
            sacrifice_flies=4,
        )
    }
    board = _build(_FakeApi(hitting=hitting), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert batter.babip is not None
    assert batter.babip == Decimal(88) / Decimal(281)


def test_babip_names_its_absences() -> None:
    """No counting line → None; an empty denominator → None with the line
    still present, so the surface can name which absence it is."""
    board = _build(_FakeApi(hitting={}), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert batter.season is None
    assert batter.babip is None

    all_whiff = {
        BATTER_ID: SeasonHittingLine(
            player_id=BATTER_ID,
            full_name="All Whiff",
            bats="L",
            games=10,
            plate_appearances=40,
            at_bats=36,
            hits=4,
            home_runs=4,
            strikeouts=32,
        )
    }
    board = _build(_FakeApi(hitting=all_whiff), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert batter.season is not None
    assert batter.babip is None  # 36 - 32 - 4 + 0 = 0 — never an invented zero


def test_the_card_carries_sprint_speed_and_the_contact_profile() -> None:
    savant = _FakeSavant(
        sprint={BATTER_ID: SprintSpeedRow(player_id=BATTER_ID, sprint_speed=Decimal("29.4"))},
        squared={
            BATTER_ID: SquaredUpRow(
                player_id=BATTER_ID,
                competitive_swings=620,
                squared_up_per_swing=Decimal("0.36"),
                avg_bat_speed=Decimal("73.4"),
            )
        },
    )
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert batter.sprint_speed_fps == Decimal("29.4")
    assert batter.squared_up_share == Decimal("0.36")
    assert batter.squared_up_swings == 620
    assert batter.squared_up_bat_speed == Decimal("73.4")


def test_the_d110_board_failures_degrade_to_named_absences() -> None:
    savant = _FakeSavant(
        expected=FetchFailure("expected-stats: HTTP 503"),
        sprint=FetchFailure("sprint-speed: HTTP 503"),
        squared=FetchFailure("squared-up: HTTP 503"),
    )
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    batter = board.games[0].away_batters[0]
    assert batter.season_gaps is None
    assert batter.sprint_speed_fps is None
    assert batter.squared_up_share is None
    joined = " ".join(board.diagnostics)
    assert "expected-stats board" in joined
    assert "sprint-speed board" in joined
    assert "squared-up board" in joined


def _pitcher_expected_row() -> ExpectedStatsRow:
    return ExpectedStatsRow(
        player_id=PITCHER_ID,
        plate_appearances=620,
        balls_in_play=450,
        batting_average=Decimal("0.240"),
        slugging=Decimal("0.410"),
        woba=Decimal("0.294"),
        expected_batting_average=Decimal("0.250"),
        expected_slugging=Decimal("0.430"),
        xwoba=Decimal("0.297"),
    )


def _pitcher_statcast_row() -> StatcastPitcherRow:
    return StatcastPitcherRow(
        player_id=PITCHER_ID,
        batted_ball_events=100,
        avg_launch_angle=Decimal("12.9"),
        barrel_count=8,
        hard_hit_count=40,
    )


def test_the_pitcher_card_carries_the_d111_season_reads() -> None:
    """D-111: wOBA/xwOBA and ISO/xISO read the expected board against (both
    sides of each pair share its denominator); barrel rate, launch angle,
    launch angle read the Statcast pitcher board; HR/9 reads the season
    line's own notation — 20 homers over "150.1" (150 and a third) innings."""
    api = _FakeApi(
        pitching={
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
                home_runs=20,
            )
        }
    )
    savant = _FakeSavant(
        pitcher_expected={PITCHER_ID: _pitcher_expected_row()},
        pitcher_statcast={PITCHER_ID: _pitcher_statcast_row()},
    )
    board = _build(api, savant)
    assert not isinstance(board, FetchFailure)
    card = board.games[0].home_pitcher
    assert card is not None
    reads = card.season_reads
    assert reads is not None
    assert reads.woba == Decimal("0.294")
    assert reads.expected_woba == Decimal("0.297")
    assert reads.iso == Decimal("0.170")
    assert reads.expected_iso == Decimal("0.180")
    assert reads.plate_appearances == 620
    assert reads.barrel_share == Decimal("0.08")
    assert reads.avg_launch_angle == Decimal("12.9")
    # D-128 (PO): the hard-hit share against reads the same board's
    # ev95plus count over its BBE sample.
    assert reads.hard_hit_share == Decimal("0.4")
    assert reads.batted_ball_events == 100
    assert reads.home_runs == 20
    assert reads.innings_text == "150.1"
    assert reads.home_run_per_nine == Decimal(180) / (Decimal(451) / Decimal(3))


def test_innings_notation_is_outs_not_tenths() -> None:
    """D-111: the fractional digit is outs (.1/.2), never tenths — anything
    outside the notation is a named absence, not a guessed divisor."""
    from greenmachine.live.pipeline import _innings_as_decimal

    assert _innings_as_decimal("150.1") == Decimal(451) / Decimal(3)
    assert _innings_as_decimal("150.2") == Decimal(452) / Decimal(3)
    assert _innings_as_decimal("150") == Decimal(150)
    assert _innings_as_decimal("150.0") == Decimal(150)
    assert _innings_as_decimal("") is None
    assert _innings_as_decimal("abc") is None
    assert _innings_as_decimal("1.3") is None
    assert _innings_as_decimal("1.10") is None


def test_the_pitcher_recent_lines_read_the_kept_events_by_side() -> None:
    """D-111, rewindowed by D-128 (PO) to the last two months: the default
    slate's kept events all belong to the starter and every one came
    against a left-handed batter, so his overall and vs-L lines carry the
    record while vs-R names its empty scope."""
    board = _build(_FakeApi(), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    card = board.games[0].home_pitcher
    assert card is not None
    overall = card.recent_overall
    assert overall is not None
    assert overall.plate_appearances == MIN_BBE_FORM
    assert overall.batted_balls == MIN_BBE_FORM
    assert overall.barrel_share == Decimal(1)
    # D-128 (PO): every fixture ball is 96 mph, so the hard-hit share
    # against is the whole record.
    assert overall.hard_hit_share == Decimal(1)
    assert overall.avg_launch_angle == Decimal("20")
    assert overall.air_ball_share == Decimal(1)
    assert overall.ground_ball_share == Decimal(0)  # D-114: all fly balls here
    assert overall.classified_batted_balls == MIN_BBE_FORM
    assert overall.woba == Decimal("0.9")
    assert overall.expected_woba is None  # the events publish no expected wOBA here
    assert overall.iso == Decimal(0)
    left = card.recent_vs_left
    assert left is not None
    assert left.plate_appearances == MIN_BBE_FORM
    assert card.recent_vs_right is None


def test_the_l30_ground_ball_share_reads_classified_bbe() -> None:
    """v2.2 (D-114): the ground-ball share is ground balls over classified
    BBE (events with a bb_type), and the classified count rides along as the
    share's true denominator — an unclassified ball leaves both counts."""
    import dataclasses

    from greenmachine.live.pipeline import _pitcher_recent_line

    base = _recent_events()[0]
    events = (
        dataclasses.replace(base, bb_type="ground_ball"),
        dataclasses.replace(base, bb_type="ground_ball"),
        dataclasses.replace(base, bb_type="fly_ball"),
        dataclasses.replace(base, bb_type="line_drive"),
        dataclasses.replace(base, bb_type=None),
    )
    line = _pitcher_recent_line(events)
    assert line is not None
    assert line.ground_ball_share == Decimal("0.5")
    assert line.classified_batted_balls == 4
    assert line.air_ball_share == Decimal("0.5")


def test_the_d111_pitcher_board_failures_degrade_to_named_absences() -> None:
    savant = _FakeSavant(
        pitcher_expected=FetchFailure("pitcher-expected-stats: HTTP 503"),
        pitcher_statcast=FetchFailure("statcast-pitchers: HTTP 503"),
    )
    board = _build(_FakeApi(), savant)
    assert not isinstance(board, FetchFailure)
    card = board.games[0].home_pitcher
    assert card is not None
    reads = card.season_reads
    assert reads is not None
    assert reads.woba is None and reads.expected_woba is None
    assert reads.iso is None and reads.expected_iso is None
    assert reads.barrel_share is None
    assert reads.avg_launch_angle is None
    assert reads.home_runs == 0  # the season line still answers
    assert reads.home_run_per_nine == Decimal(0)  # zero homers allowed is a real zero
    joined = " ".join(board.diagnostics)
    assert "pitcher expected-stats board" in joined
    assert "statcast pitcher board" in joined


def _build_with_humidity(api: object, humidity: object) -> object:
    def fetch_day(day: date) -> tuple[PitchEvent, ...]:
        return tuple(e for e in _recent_events() if e.game_date == day.isoformat())

    return build_board(
        api=api,  # type: ignore[arg-type]
        savant=_FakeSavant(),  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        fetch_day_events=fetch_day,
        temperature_for=lambda venue: Decimal("78"),
        park_factors=_park_factors(),
        humidity_for=humidity,  # type: ignore[arg-type]
    )


def test_humidity_reaches_an_open_air_game_card_only() -> None:
    """D-111: humidity rides the wind rule — an open-air venue's reading
    reaches the card; a roofed venue carries no reading that never applied."""
    board = _build_with_humidity(_OpenAirApi(), lambda venue: Decimal("42"))
    assert not isinstance(board, FetchFailure)
    assert board.games[0].relative_humidity_percent == Decimal("42")
    roofed = _build_with_humidity(_FakeApi(), lambda venue: Decimal("42"))
    assert not isinstance(roofed, FetchFailure)
    assert roofed.games[0].relative_humidity_percent is None


def test_the_mix_reach_never_stretches_the_form_fallback_window() -> None:
    """D-103: when a starter's empty L30 forces the L45 mix reach, the form
    section's L14 fallback must still read exactly 14 days — before the fix,
    the rebound ``reach_start`` leaked 45 days into a window labelled L14."""
    old_barrel = _window_event(
        game_date="2026-07-31", pitcher_id=999
    )  # 20 days out: past L14; from another pitcher so the starter's L30 stays empty
    stale_starter_pitch = _window_event(
        game_date="2026-07-15", batter_id=909
    )  # the starter has nothing in L30, so the mix reach fires
    board = _build(_FakeApi(), _FakeSavant(), events=(old_barrel, stale_starter_pitch))
    assert not isinstance(board, FetchFailure)
    form = board.games[0].away_batters[0].form
    assert form is not None
    assert form.barrel_pct.value is None
    assert form.barrel_pct.sample == 0

    # Anti-vacuity: the same barrel ten days out IS inside the honest L14.
    in_reach = _window_event(game_date="2026-08-10", pitcher_id=999)
    board = _build(_FakeApi(), _FakeSavant(), events=(in_reach, stale_starter_pitch))
    assert not isinstance(board, FetchFailure)
    form = board.games[0].away_batters[0].form
    assert form is not None
    assert form.barrel_pct.value == Decimal("100")
    assert form.barrel_pct.window_days == 14
    assert form.barrel_pct.sample == 1


def test_money_tag_marks_a_homer_on_the_slate_day() -> None:
    """D-130 (PO): the tag answers "who got the day of the slate I'm
    looking at" — a homer ON the slate day tags, carrying the day; a
    homer on any other day does not (the slate here is 2026-08-20)."""
    logs = {
        BATTER_ID: (
            _log_entry("2026-08-12", home_runs=1),
            _log_entry("2026-08-20", home_runs=1),
        )
    }
    board = _build(_FakeApi(game_logs=logs), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_slate_day == "2026-08-20"

    last_night_only = {
        BATTER_ID: (
            _log_entry("2026-08-12", home_runs=1),
            _log_entry("2026-08-19", home_runs=1),
        )
    }
    board = _build(_FakeApi(game_logs=last_night_only), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_slate_day is None


def test_money_tag_stays_off_without_a_homer_in_the_record() -> None:
    """D-130/D-100: no home run on the slate day, no tag — never a guess.
    No log at all is also no tag (a pre-game slate's exact state)."""
    logs = {BATTER_ID: (_log_entry("2026-08-20", home_runs=0),)}
    board = _build(_FakeApi(game_logs=logs), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_slate_day is None

    board = _build(_FakeApi(), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_slate_day is None


def test_money_tag_stays_off_when_the_log_source_fails() -> None:
    """D-100: a failed game-log fetch downgrades to absence — no tag, and
    the build still completes."""
    board = _build(_FakeApi(game_logs=FetchFailure("game-logs: HTTP 503")), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_slate_day is None
