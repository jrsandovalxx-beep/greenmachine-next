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
        game_logs: dict[int, tuple[GameLogEntry, ...]] | FetchFailure | None = None,
    ) -> None:
        self._orders = orders
        self._game_logs = game_logs
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
    slider = lines["SL"]
    assert slider.usage_share == Decimal(1) / Decimal(4)
    # A pitch thrown but never put in play carries named absences, not zeros.
    assert slider.plate_appearances == 0
    assert slider.batting_average is None
    assert slider.barrel_share is None
    assert slider.whiff_share is None


def test_pitch_lines_sort_by_usage_and_empty_scope_is_absent() -> None:
    from greenmachine.live.pipeline import _pitch_lines

    assert _pitch_lines(()) == ()
    events = tuple(
        _window_event(pitch_type="FF" if index else "CH", event="") for index in range(3)
    )
    assert [line.pitch_type for line in _pitch_lines(events)] == ["FF", "CH"]


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


def test_batter_matchup_lines_are_side_scoped_over_the_window() -> None:
    """D-088: the matchup table counts only pitches from the opposing
    starter's side inside the matchup window — same-side pitching and older
    pitches never enter a denominator. With no probable named there is no
    scope and the card carries no lines."""
    events = (
        _window_event(pitch_type="FF", pitcher_throws="R"),
        _window_event(pitch_type="FF", pitcher_throws="R"),
        _window_event(pitch_type="SL", pitcher_throws="L"),  # wrong side
        _window_event(
            pitch_type="CU", pitcher_throws="R", game_date="2026-07-10"
        ),  # outside the window
    )
    board = _build(_FakeApi(), _FakeSavant(), events=events)
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    # The away lineup faces the home probable, a right-hander.
    away = game.away_batters[0]
    assert [line.pitch_type for line in away.pitch_lines] == ["FF"]
    assert away.pitch_lines[0].pitches == 2
    assert away.pitch_lines[0].usage_share == Decimal(1)
    # The home lineup has no named opposing starter: no scope, no lines.
    assert game.home_batters[0].pitch_lines == ()


def test_mix_line_counts_only_the_qualifying_mix_pitches() -> None:
    """D-079: the grid line reads the batter's L30 events against the
    starter's qualifying (>=14% usage) mix pitches — a fringe pitch the
    starter barely throws never enters a denominator. With no probable
    named there is no scope and no line (D-081)."""
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
    assert away.mix_label == "last 30 days"
    line = away.mix_line
    assert line is not None
    assert line.pitches == 4
    assert line.at_bats == 4
    assert line.hits == 4  # the four SL events are outside the qualifying mix
    assert board.games[0].home_batters[0].mix_line is None


def test_mix_reaches_back_to_l45_only_when_the_window_is_empty() -> None:
    """D-081: a starter with no pitches in the matchup window extends the
    read to L45, named on the surface; the extra days are fetched only when
    some probable needs them."""
    old_starter_events = (
        _window_event(
            batter_id=555, pitcher_id=PITCHER_ID, pitch_type="FF", game_date="2026-07-20"
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
    assert away.mix_label == "last 45 days"
    assert min(fetched) == date(2026, 7, 6)  # the reach fetched days 31-45 back
    line = away.mix_line
    assert line is not None
    assert line.at_bats == 1

    # No empty-window starter: the reach never fires.
    fetched.clear()
    recent_starter = (_window_event(batter_id=555, pitcher_id=PITCHER_ID, pitch_type="FF"),)
    current_events = recent_starter + batter_events

    def fetch_current_day(day: date) -> tuple[PitchEvent, ...]:
        fetched.append(day)
        return tuple(e for e in current_events if e.game_date == day.isoformat())

    board = build_board(
        api=_FakeApi(),  # type: ignore[arg-type]
        savant=_FakeSavant(),  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=CONFIG,
        fetch_day_events=fetch_current_day,
        temperature_for=lambda venue: Decimal("78"),
        park_factors=_park_factors(),
    )
    assert not isinstance(board, FetchFailure)
    assert min(fetched) == date(2026, 7, 21)  # the plain 31-day window only


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


def test_distance_350_counts_long_balls_in_any_direction() -> None:
    """D-090/D-097: the +350 ft count tallies batted balls at or past the
    distance floor in any direction — short balls and non-batted pitches
    never enter the tally."""
    pull_x, oppo_x = Decimal("100"), Decimal("150")  # L batter: spray < 0 pulls
    base = {
        "pitch_type": "FF",
        "launch_speed": Decimal("100"),
        "hc_y": Decimal("150"),
        "event": "fly_out",
    }
    events = (
        _window_event(bb_type="fly_ball", hc_x=pull_x, hit_distance=Decimal("380"), **base),
        _window_event(bb_type="fly_ball", hc_x=pull_x, hit_distance=Decimal("320"), **base),
        _window_event(bb_type="fly_ball", hc_x=oppo_x, hit_distance=Decimal("390"), **base),
        _window_event(bb_type="ground_ball", hc_x=pull_x, hit_distance=Decimal("400"), **base),
        _window_event(
            event="",
            launch_speed=None,
            launch_angle=None,
            launch_speed_angle=None,
            description="ball",
        ),
    )
    board = _build(_FakeApi(), _FakeSavant(), events=events)
    assert not isinstance(board, FetchFailure)
    line = board.games[0].away_batters[0].mix_line
    assert line is not None
    assert line.batted_balls == 4
    # 380 pull, 390 oppo, and the 400-ft grounder all count: distance only.
    assert line.distance_350_count == 3


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
    assert line.distance_350_count == 2  # the 390 and 380: distance only


def test_season_grid_line_composes_the_season_sources() -> None:
    """D-079's toggle target: the season line reads the hitting line
    (AVG/SLG/ISO from total bases), the statcast board (EV, barrels,
    hard-hit), and the arsenal board (PA-weighted xwOBA, pitch-weighted
    Swing-Str). No season source publishes a 350-foot pull-air read."""
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
    assert line.distance_350_count is None
    assert line.pull_air_share is None


def _log_entry(date: str, home_runs: int, plate_appearances: int = 4) -> GameLogEntry:
    return GameLogEntry(
        date=date,
        game_pk=777001,
        home_runs=home_runs,
        plate_appearances=plate_appearances,
    )


def test_money_tag_marks_a_homer_in_the_last_game_day() -> None:
    """D-094/D-100: the tag follows the most recent completed game in the
    log — homer that day, tag; homer earlier with a quieter game after,
    no tag."""
    logs = {
        BATTER_ID: (
            _log_entry("2026-08-12", home_runs=1),
            _log_entry("2026-08-18", home_runs=1),
        )
    }
    board = _build(_FakeApi(game_logs=logs), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_last_game_day is True

    quieter_after = {
        BATTER_ID: (
            _log_entry("2026-08-12", home_runs=1),
            _log_entry("2026-08-18", home_runs=0),
            _log_entry("2026-08-19", home_runs=0),
        )
    }
    board = _build(_FakeApi(game_logs=quieter_after), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_last_game_day is False


def test_money_tag_stays_off_without_a_homer_in_the_record() -> None:
    """D-094/D-100: no home run in the game log, no tag — never a guess.
    No log at all is also no tag."""
    logs = {BATTER_ID: (_log_entry("2026-08-19", home_runs=0),)}
    board = _build(_FakeApi(game_logs=logs), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_last_game_day is False

    board = _build(_FakeApi(), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_last_game_day is False


def test_money_tag_stays_off_when_the_log_source_fails() -> None:
    """D-100: a failed game-log fetch downgrades to absence — no tag, and
    the build still completes."""
    board = _build(_FakeApi(game_logs=FetchFailure("game-logs: HTTP 503")), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_last_game_day is False


def test_money_tag_ignores_zero_pa_entries() -> None:
    """D-100: a log line without plate appearances is not a played game —
    it neither tags nor clears."""
    logs = {
        BATTER_ID: (
            _log_entry("2026-08-18", home_runs=1),
            _log_entry("2026-08-19", home_runs=0, plate_appearances=0),
        )
    }
    board = _build(_FakeApi(game_logs=logs), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    assert board.games[0].away_batters[0].homered_on_last_game_day is True
