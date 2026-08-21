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
    ProbablePitcher,
    ScheduledGame,
    SeasonHittingLine,
    SeasonPitchingLine,
    Slate,
)
from greenmachine.live.pipeline import build_board
from greenmachine.live.savant import (
    BatTrackingRow,
    PitchArsenalRow,
    PitchEvent,
    StatcastBatterRow,
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
    ) -> None:
        self._orders = orders
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


class _FakeSavant:
    def __init__(
        self,
        *,
        batter_arsenal: tuple[PitchArsenalRow, ...] | FetchFailure = (),
        pitcher_arsenal: tuple[PitchArsenalRow, ...] | FetchFailure = (),
    ) -> None:
        self._batter_arsenal = batter_arsenal
        self._pitcher_arsenal = pitcher_arsenal

    def fetch_pitch_arsenal(
        self, *, kind: str, year: int
    ) -> tuple[PitchArsenalRow, ...] | FetchFailure:
        return self._batter_arsenal if kind == "batter" else self._pitcher_arsenal

    def fetch_statcast_batters(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, StatcastBatterRow]:
        return {BATTER_ID: _statcast_row(BATTER_ID)}

    def fetch_bat_tracking(
        self, *, year: int, minimum: int = 0, start: str = "", end: str = ""
    ) -> tuple[BatTrackingRow, ...]:
        return (_tracking_row(BATTER_ID),)


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
