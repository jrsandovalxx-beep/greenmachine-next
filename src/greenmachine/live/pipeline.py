"""Slate assembly: fetch the day, join the boards, grade every batter (GMF-006).

The composition root for the live dashboard. It reads the two live sources
through injected adapters, joins them against the pinned park reference and
park-factor snapshot, and produces a :class:`SlateBoard` of graded cards. Every
fetch failure degrades to a named absence on the affected components and a
line in ``SlateBoard.diagnostics`` — the board always renders what it has.

Judgment calls logged in D-073:

- an unposted batting order is replaced by the club's nine highest-usage
  bats on the arsenal board, labelled as an estimate;
- a venue with any roof grades conditions at the neutral indoor value;
  only open-air venues use the live forecast (roof state is not sourced in
  v1, and an unobtained roof may be closed);
- form windows close at ``as_of`` and reach back over the D-068 fallback
  reach, with each metric preferring its short window independently.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from greenmachine.config.schema import GreenMachineConfig
from greenmachine.domain.entities import Batter, GameContext, Pitcher, Venue
from greenmachine.domain.enums import PitcherRole
from greenmachine.domain.grade_result import EvaluatedGradeResult, NotEvaluableGradeResult
from greenmachine.domain.values import GameId, PlayerId, SourceCaptureId, VenueId
from greenmachine.inputs.contract import Handedness, ParkFactor, ParkVenue, VenueType
from greenmachine.inputs.park_reference import PARK_VENUES
from greenmachine.live.form import (
    BARREL_CLASSIFICATION,
    HARD_HIT_THRESHOLD_MPH,
    FormSection,
    aggregate_form,
    resolve_form_section,
)
from greenmachine.live.grading import (
    QUALIFYING_USAGE_SHARE,
    BatterGradingInput,
    MatchupInput,
    grade_batter,
    league_baselines,
    resolve_batting_side,
)
from greenmachine.live.mlb_api import (
    FetchFailure,
    MlbStatsApi,
    SeasonHittingLine,
    SeasonPitchingLine,
)
from greenmachine.live.savant import (
    BaseballSavant,
    BatTrackingRow,
    PitchArsenalRow,
    PitchEvent,
    StatcastBatterRow,
)

FORM_REACH_DAYS = 14
FORM_SHORT_DAYS = 7
# The batter's matchup table reads his pitches seen against the
# opposing starter's side over this many days (D-088).
MATCHUP_WINDOW_DAYS = 30
SEASON_WINDOW_MONTH = 3
SEASON_WINDOW_DAY = 1
SEASON_IDS_PER_REQUEST = 90
FALLBACK_LINEUP_SIZE = 9

# IANA zones per MLBAM venue id, derived from the park reference's club
# mapping: one zone per club city, transcribed once and pinned by test.
_CLUB_TIMEZONES: dict[str, str] = {
    "Arizona Diamondbacks": "America/Phoenix",
    "Athletics": "America/Los_Angeles",
    "Atlanta Braves": "America/New_York",
    "Baltimore Orioles": "America/New_York",
    "Boston Red Sox": "America/New_York",
    "Chicago Cubs": "America/Chicago",
    "Chicago White Sox": "America/Chicago",
    "Cincinnati Reds": "America/New_York",
    "Cleveland Guardians": "America/New_York",
    "Colorado Rockies": "America/Denver",
    "Detroit Tigers": "America/New_York",
    "Houston Astros": "America/Chicago",
    "Kansas City Royals": "America/Chicago",
    "Los Angeles Angels": "America/Los_Angeles",
    "Los Angeles Dodgers": "America/Los_Angeles",
    "Miami Marlins": "America/New_York",
    "Milwaukee Brewers": "America/Chicago",
    "Minnesota Twins": "America/Chicago",
    "New York Mets": "America/New_York",
    "New York Yankees": "America/New_York",
    "Philadelphia Phillies": "America/New_York",
    "Pittsburgh Pirates": "America/New_York",
    "San Diego Padres": "America/Los_Angeles",
    "San Francisco Giants": "America/Los_Angeles",
    "Seattle Mariners": "America/Los_Angeles",
    "St. Louis Cardinals": "America/Chicago",
    "Tampa Bay Rays": "America/New_York",
    "Texas Rangers": "America/Chicago",
    "Toronto Blue Jays": "America/New_York",
    "Washington Nationals": "America/New_York",
}

# Stats API club name -> the arsenal board's alt code (for roster fallback).
TEAM_ABBREVIATIONS: dict[str, str] = {
    "Arizona Diamondbacks": "ARI",
    "Athletics": "ATH",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD",
    "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH",
}

VENUE_TIMEZONES: dict[int, str] = {
    venue.savant_venue_id: _CLUB_TIMEZONES[venue.team]
    for venue in PARK_VENUES
    if venue.savant_venue_id is not None
}

_VENUE_BY_SAVANT_ID: dict[int, ParkVenue] = {
    venue.savant_venue_id: venue for venue in PARK_VENUES if venue.savant_venue_id is not None
}
_VENUE_BY_TEAM: dict[str, ParkVenue] = {venue.team: venue for venue in PARK_VENUES}


@dataclass(frozen=True)
class PitchLine:
    """One pitch type's line in the expanded matchup view (D-080).

    Every figure is computed here, pipeline-side, over a stated scope — the
    view formats, never derives (§GMF-008). ``usage_share`` is the pitch's
    share of the scope's pitches; the rate columns are None where their
    denominator is empty, so the surface names the absence instead of
    inventing a zero.
    """

    pitch_type: str
    pitch_name: str
    pitches: int
    usage_share: Decimal
    plate_appearances: int
    batting_average: Decimal | None
    slugging: Decimal | None
    iso: Decimal | None
    home_runs: int | None  # None where the scope's source publishes no count
    barrel_share: Decimal | None
    hard_hit_share: Decimal | None
    expected_woba: Decimal | None
    whiff_share: Decimal | None
    woba: Decimal | None = None  # the arsenal board's own wOBA (season scopes)
    strikeout_share: Decimal | None = None  # the arsenal board's K% (season scopes)


@dataclass(frozen=True)
class BatterCard:
    """One graded batter: display rows plus the full domain result."""

    player_id: int
    full_name: str
    team: str
    bats: str
    batting_side: str | None
    order_position: int | None
    lineup_is_estimate: bool
    season: SeasonHittingLine | None
    statcast: StatcastBatterRow | None
    form: FormSection | None
    recent_events: tuple[PitchEvent, ...]
    pitch_lines: tuple[PitchLine, ...]
    result: EvaluatedGradeResult | NotEvaluableGradeResult


@dataclass(frozen=True)
class PitcherCard:
    """The expected opposing pitcher: season line, qualifying arsenal, and the
    season-long per-pitch lines the Arsenal table shows (D-087). Pitcher
    metrics are always season figures — never windowed — with last season
    filling in when he has no current record; the only window read is the
    per-side pitch-type set behind the table's side filter."""

    player_id: int
    full_name: str
    throws: str
    season: SeasonPitchingLine | None
    arsenal: tuple[PitchArsenalRow, ...]
    season_lines: tuple[PitchLine, ...]
    season_lines_year: int
    pitches_vs_left: frozenset[str]
    pitches_vs_right: frozenset[str]


@dataclass(frozen=True)
class GameCard:
    """One game: venue, probables, and both lineups as graded batter cards."""

    game_pk: int
    status: str
    scheduled_start_utc: datetime
    venue_name: str
    venue_type: VenueType
    home_team: str
    away_team: str
    home_pitcher: PitcherCard | None
    away_pitcher: PitcherCard | None
    home_batters: tuple[BatterCard, ...]
    away_batters: tuple[BatterCard, ...]
    temperature_fahrenheit: Decimal | None
    wind_speed_mph: Decimal | None
    wind_direction: str | None
    home_run_factor_left: ParkFactor | None
    home_run_factor_right: ParkFactor | None


@dataclass(frozen=True)
class SlateBoard:
    """The full slate view the four tabs render."""

    official_date: str
    as_of: datetime
    games: tuple[GameCard, ...]
    diagnostics: tuple[str, ...]


def _recent_window_events(
    events: tuple[PitchEvent, ...], cap_games: int = 7
) -> tuple[PitchEvent, ...]:
    """The batter's events from the most recent games in the form window,
    newest game first — the exit-velocity log's rows (D-086). Every pitch of
    a kept game is carried: the pitch mix needs the full counts, and the
    sheet's threshold toggle is a view filter over these rows, not a data
    cut. Source is the same form-window feed the form section reads.
    """
    dates = sorted({event.game_date for event in events}, reverse=True)[:cap_games]
    keep = set(dates)
    kept = [event for event in events if event.game_date in keep]
    order = {day: index for index, day in enumerate(dates)}
    return tuple(sorted(kept, key=lambda event: order[event.game_date]))


_PITCH_NAMES: dict[str, str] = {
    "FF": "4-Seam Fastball",
    "FA": "Fastball",
    "SI": "Sinker",
    "FC": "Cutter",
    "SL": "Slider",
    "ST": "Sweeper",
    "SV": "Slurve",
    "CU": "Curveball",
    "KC": "Knuckle Curve",
    "CS": "Slow Curve",
    "CH": "Changeup",
    "FS": "Splitter",
    "FO": "Forkball",
    "EP": "Eephus",
    "KN": "Knuckleball",
    "SC": "Screwball",
    "PO": "Pitch Out",
}

# Plate-appearance endings that do not consume an at-bat; per-pitch AVG and
# SLG divide by at-bats, so these leave the denominator.
_NON_AT_BAT_EVENTS = frozenset({"walk", "hit_by_pitch", "sac_fly", "sac_bunt", "catcher_interf"})
_HIT_BASES = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
_SWING_DESCRIPTIONS = frozenset(
    {
        "swinging_strike",
        "swinging_strike_blocked",
        "foul_tip",
        "foul",
        "foul_bunt",
        "missed_bunt",
        "hit_into_play",
    }
)
_WHIFF_DESCRIPTIONS = frozenset(
    {"swinging_strike", "swinging_strike_blocked", "foul_tip", "missed_bunt"}
)


def _pitch_lines(events: Sequence[PitchEvent]) -> tuple[PitchLine, ...]:
    """Per-pitch-type lines over one stated scope of pitch events (§GMF-008).

    The caller chooses the scope — every pitch the pitcher threw in the form
    window, or only those against batters of one side — and every figure here
    derives from exactly those events, so the two toggle positions can never
    disagree about their denominators. Rate columns are None where their
    denominator is empty: the surface names the absence rather than inventing
    a zero. Lines come back sorted by usage, heaviest first.
    """
    if not events:
        return ()
    by_pitch: dict[str, list[PitchEvent]] = {}
    for event in events:
        by_pitch.setdefault(event.pitch_type, []).append(event)
    lines: list[PitchLine] = []
    total = len(events)
    for pitch_type, group in by_pitch.items():
        ending = [event for event in group if event.event]
        at_bats = sum(1 for event in ending if event.event not in _NON_AT_BAT_EVENTS)
        hits = sum(1 for event in ending if event.event in _HIT_BASES)
        bases = sum(_HIT_BASES.get(event.event, 0) for event in ending)
        average = Decimal(hits) / Decimal(at_bats) if at_bats else None
        slugging = Decimal(bases) / Decimal(at_bats) if at_bats else None
        batted = [event for event in group if event.launch_speed is not None]
        barrels = sum(1 for event in batted if event.launch_speed_angle == BARREL_CLASSIFICATION)
        hard_hits = sum(
            1
            for event in batted
            if event.launch_speed is not None and event.launch_speed >= HARD_HIT_THRESHOLD_MPH
        )
        woba_ending = [
            event for event in ending if event.estimated_woba is not None and event.woba_denom
        ]
        woba_total = sum(
            (event.estimated_woba for event in woba_ending if event.estimated_woba is not None),
            Decimal(0),
        )
        woba_denominator = sum(
            (event.woba_denom for event in woba_ending if event.woba_denom is not None),
            Decimal(0),
        )
        swings = sum(1 for event in group if event.description in _SWING_DESCRIPTIONS)
        whiffs = sum(1 for event in group if event.description in _WHIFF_DESCRIPTIONS)
        lines.append(
            PitchLine(
                pitch_type=pitch_type,
                pitch_name=_PITCH_NAMES.get(pitch_type, pitch_type),
                pitches=len(group),
                usage_share=Decimal(len(group)) / Decimal(total),
                plate_appearances=len(ending),
                batting_average=average,
                slugging=slugging,
                iso=(slugging - average if average is not None and slugging is not None else None),
                home_runs=sum(1 for event in ending if event.event == "home_run"),
                barrel_share=Decimal(barrels) / Decimal(len(batted)) if batted else None,
                hard_hit_share=Decimal(hard_hits) / Decimal(len(batted)) if batted else None,
                expected_woba=(woba_total / woba_denominator) if woba_denominator else None,
                whiff_share=Decimal(whiffs) / Decimal(swings) if swings else None,
            )
        )
    lines.sort(key=lambda line: line.usage_share, reverse=True)
    return tuple(lines)


def _season_pitch_lines(rows: Sequence[PitchArsenalRow]) -> tuple[PitchLine, ...]:
    """Season-long per-pitch lines from the arsenal board — the pitcher's
    whole year, never a window (D-087). The board publishes no home-run or
    barrel counts, so those cells stay None: the surface names the absence
    rather than inventing a zero. Lines come back sorted by usage, heaviest
    first.
    """
    lines = [
        PitchLine(
            pitch_type=row.pitch_type,
            pitch_name=row.pitch_name,
            pitches=row.pitches,
            usage_share=row.usage_share,
            plate_appearances=row.plate_appearances,
            batting_average=row.batting_average,
            slugging=row.slugging,
            iso=row.slugging - row.batting_average,
            home_runs=None,
            barrel_share=None,
            hard_hit_share=row.hard_hit_share,
            expected_woba=row.expected_woba,
            whiff_share=row.whiff_share,
            woba=row.woba,
            strikeout_share=row.strikeout_share,
        )
        for row in rows
    ]
    lines.sort(key=lambda line: line.usage_share, reverse=True)
    return tuple(lines)


def _chunked(ids: tuple[int, ...], size: int) -> list[tuple[int, ...]]:
    return [ids[index : index + size] for index in range(0, len(ids), size)]


def _parse_start(raw: str, official_date: str) -> datetime:
    """The scheduled first pitch as a UTC instant; midday UTC when unlisted."""
    if raw:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.astimezone(UTC)
    day = date.fromisoformat(official_date)
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=UTC)


def _season_window_start(day: date) -> datetime:
    return datetime(day.year, SEASON_WINDOW_MONTH, SEASON_WINDOW_DAY, tzinfo=UTC)


def _team_venue(venue_id: int, home_team: str) -> ParkVenue | None:
    """Join the scheduled game to the park reference; id first, club second."""
    venue = _VENUE_BY_SAVANT_ID.get(venue_id)
    if venue is not None:
        return venue
    return _VENUE_BY_TEAM.get(home_team)


def _side_resolved_tracking(
    rows: tuple[BatTrackingRow, ...], side: str | None
) -> tuple[BatTrackingRow, ...]:
    """The resolved side's tracking rows; both sides when unresolved (D-065)."""
    if side is None:
        return rows
    return tuple(row for row in rows if row.side == side)


def _fallback_order(
    team: str,
    batter_arsenal_rows: tuple[PitchArsenalRow, ...],
) -> tuple[int, ...]:
    """The club's highest-usage bats as an estimated lineup (D-073).

    Usage is the summed plate appearances on the batter arsenal board — a
    playing-time proxy, labelled as an estimate wherever it renders.
    """
    code = TEAM_ABBREVIATIONS.get(team)
    if code is None:
        return ()
    usage: dict[int, int] = {}
    for row in batter_arsenal_rows:
        if row.team == code:
            usage[row.player_id] = usage.get(row.player_id, 0) + row.plate_appearances
    ranked = sorted(usage.items(), key=lambda item: item[1], reverse=True)
    return tuple(player_id for player_id, _ in ranked[:FALLBACK_LINEUP_SIZE])


def fetch_window_events(
    fetch_day: Callable[[date], tuple[PitchEvent, ...] | FetchFailure],
    *,
    days: tuple[date, ...],
    keep: Callable[[PitchEvent], bool] | None = None,
) -> tuple[tuple[PitchEvent, ...], tuple[str, ...]]:
    """Aggregate per-day event fetches; a failed day is named, not fatal.

    ``keep`` trims each day to the events the board can use — the slate's
    batters and probables — so a long matchup window never swells memory with
    pitches involving players no surface reads.
    """
    events: list[PitchEvent] = []
    diagnostics: list[str] = []
    for day in days:
        fetched = fetch_day(day)
        if isinstance(fetched, FetchFailure):
            diagnostics.append(f"pitch events for {day.isoformat()}: {fetched.reason}")
            continue
        if keep is None:
            events.extend(fetched)
        else:
            events.extend(event for event in fetched if keep(event))
    return tuple(events), tuple(diagnostics)


def _pitcher_card(
    probable_id: int,
    probable_name: str,
    season_pitching: dict[int, SeasonPitchingLine],
    pitcher_arsenal: dict[int, tuple[PitchArsenalRow, ...]],
    fallback_arsenal: dict[int, tuple[PitchArsenalRow, ...]],
    season_year: int,
    window_events: tuple[PitchEvent, ...],
) -> PitcherCard:
    season = season_pitching.get(probable_id)
    current_rows = pitcher_arsenal.get(probable_id, ())
    if current_rows:
        season_rows = current_rows
        lines_year = season_year
    else:
        # No current-season record: last season fills in, labelled (D-087).
        season_rows = fallback_arsenal.get(probable_id, ())
        lines_year = season_year - 1 if season_rows else season_year
    return PitcherCard(
        player_id=probable_id,
        full_name=probable_name or (season.full_name if season else f"Player {probable_id}"),
        throws=season.throws if season else "",
        season=season,
        arsenal=tuple(row for row in current_rows if row.usage_share >= QUALIFYING_USAGE_SHARE),
        season_lines=_season_pitch_lines(season_rows),
        season_lines_year=lines_year,
        pitches_vs_left=frozenset(
            event.pitch_type
            for event in window_events
            if event.batter_side == "L" and event.pitch_type
        ),
        pitches_vs_right=frozenset(
            event.pitch_type
            for event in window_events
            if event.batter_side == "R" and event.pitch_type
        ),
    )


def _game_context(
    game_pk: int,
    official_date: str,
    start_utc: datetime,
    venue: ParkVenue | None,
    venue_id: int,
    venue_name: str,
) -> GameContext:
    """The game's scheduling identity. An unjoined venue keeps the schedule's
    own id and name with a UTC timezone rather than borrowing another park."""
    timezone = (
        VENUE_TIMEZONES.get(venue.savant_venue_id, "UTC")
        if venue is not None and venue.savant_venue_id is not None
        else "UTC"
    )
    local = start_utc.astimezone(ZoneInfo(timezone))
    return GameContext(
        game_id=GameId(str(game_pk)),
        slate_date=date.fromisoformat(official_date),
        scheduled_start_utc=start_utc,
        venue_local_scheduled_time=local,
        venue=Venue(
            venue_id=VenueId(str(venue_id)),
            name=venue_name,
            timezone=timezone,
        ),
    )


def build_board(
    *,
    api: MlbStatsApi,
    savant: BaseballSavant,
    slate_date: date,
    as_of: datetime,
    config: GreenMachineConfig,
    fetch_day_events: Callable[[date], tuple[PitchEvent, ...] | FetchFailure],
    temperature_for: Callable[[ParkVenue], Decimal | None],
    park_factors: dict[int, dict[Handedness, ParkFactor]],
    wind_for: Callable[[ParkVenue], tuple[Decimal, str] | None] = lambda venue: None,
) -> SlateBoard | FetchFailure:
    """Assemble and grade the full slate. Only a slate-level failure is fatal."""
    diagnostics: list[str] = []
    slate = api.fetch_slate(slate_date.strftime("%m/%d/%Y"))
    if isinstance(slate, FetchFailure):
        return slate

    year = slate_date.year
    batter_arsenal_result = savant.fetch_pitch_arsenal(kind="batter", year=year)
    batter_arsenal: tuple[PitchArsenalRow, ...]
    batter_arsenal_available = not isinstance(batter_arsenal_result, FetchFailure)
    if isinstance(batter_arsenal_result, FetchFailure):
        diagnostics.append(f"batter arsenal board: {batter_arsenal_result.reason}")
        batter_arsenal = ()
    else:
        batter_arsenal = batter_arsenal_result
        if not batter_arsenal:
            diagnostics.append("batter arsenal board: returned zero rows")
    pitcher_arsenal_result = savant.fetch_pitch_arsenal(kind="pitcher", year=year)
    pitcher_arsenal_rows: tuple[PitchArsenalRow, ...]
    pitcher_arsenal_available = not isinstance(pitcher_arsenal_result, FetchFailure)
    if isinstance(pitcher_arsenal_result, FetchFailure):
        diagnostics.append(f"pitcher arsenal board: {pitcher_arsenal_result.reason}")
        pitcher_arsenal_rows = ()
    else:
        pitcher_arsenal_rows = pitcher_arsenal_result
        if not pitcher_arsenal_rows:
            diagnostics.append("pitcher arsenal board: returned zero rows")
    league = league_baselines(batter_rows=batter_arsenal, pitcher_rows=pitcher_arsenal_rows)
    arsenal_lists_by_pitcher: dict[int, list[PitchArsenalRow]] = {}
    for row in pitcher_arsenal_rows:
        arsenal_lists_by_pitcher.setdefault(row.player_id, []).append(row)
    arsenal_by_pitcher = {
        player_id: tuple(rows) for player_id, rows in arsenal_lists_by_pitcher.items()
    }
    arsenal_lists_by_batter: dict[int, list[PitchArsenalRow]] = {}
    for row in batter_arsenal:
        arsenal_lists_by_batter.setdefault(row.player_id, []).append(row)
    arsenal_by_batter = {
        player_id: tuple(rows) for player_id, rows in arsenal_lists_by_batter.items()
    }

    # Pitcher metrics are season figures with a last-season fallback (D-087):
    # a probable with no current-season arsenal row reads his prior-year board
    # instead, fetched once and only when someone needs it.
    fallback_arsenal_by_pitcher: dict[int, tuple[PitchArsenalRow, ...]] = {}

    # Lineups: the posted order, else the estimated one, flagged.
    lineup_ids: dict[tuple[int, str], tuple[int, ...]] = {}
    lineup_estimated: set[tuple[int, str]] = set()
    for game in slate.games:
        orders = api.fetch_batting_orders(game.game_pk)
        if isinstance(orders, FetchFailure):
            diagnostics.append(f"batting orders for game {game.game_pk}: {orders.reason}")
            home_order: tuple[int, ...] = ()
            away_order: tuple[int, ...] = ()
        else:
            home_order = orders.home
            away_order = orders.away
        for team, order in ((game.home_team, home_order), (game.away_team, away_order)):
            key = (game.game_pk, team)
            if order:
                lineup_ids[key] = order
            else:
                lineup_ids[key] = _fallback_order(team, batter_arsenal)
                lineup_estimated.add(key)

    all_batter_ids = tuple({pid for ids in lineup_ids.values() for pid in ids})
    probable_ids = tuple(
        {
            probable.player_id
            for game in slate.games
            for probable in (game.home_probable, game.away_probable)
            if probable is not None
        }
    )

    missing_current = {pid for pid in probable_ids if not arsenal_by_pitcher.get(pid)}
    if missing_current and pitcher_arsenal_available:
        fallback_result = savant.fetch_pitch_arsenal(kind="pitcher", year=year - 1)
        if isinstance(fallback_result, FetchFailure):
            diagnostics.append(f"pitcher arsenal fallback ({year - 1}): {fallback_result.reason}")
        else:
            fallback_lists: dict[int, list[PitchArsenalRow]] = {}
            for row in fallback_result:
                if row.player_id in missing_current:
                    fallback_lists.setdefault(row.player_id, []).append(row)
            fallback_arsenal_by_pitcher = {
                player_id: tuple(rows) for player_id, rows in fallback_lists.items()
            }

    season_hitting: dict[int, SeasonHittingLine] = {}
    for chunk in _chunked(all_batter_ids, SEASON_IDS_PER_REQUEST):
        fetched = api.fetch_season_hitting(chunk)
        if isinstance(fetched, FetchFailure):
            diagnostics.append(f"season hitting: {fetched.reason}")
            continue
        season_hitting.update(fetched)

    season_pitching: dict[int, SeasonPitchingLine] = {}
    if probable_ids:
        fetched_pitching = api.fetch_season_pitching(probable_ids)
        if isinstance(fetched_pitching, FetchFailure):
            diagnostics.append(f"season pitching: {fetched_pitching.reason}")
        else:
            season_pitching = fetched_pitching

    statcast_result = savant.fetch_statcast_batters(year=year)
    statcast: dict[int, StatcastBatterRow]
    if isinstance(statcast_result, FetchFailure):
        diagnostics.append(f"statcast board: {statcast_result.reason}")
        statcast = {}
    else:
        statcast = statcast_result
        if not statcast:
            diagnostics.append("statcast board: returned zero rows")

    short_start = (as_of - timedelta(days=FORM_SHORT_DAYS)).date()
    reach_start = (as_of - timedelta(days=FORM_REACH_DAYS)).date()
    tracking_short_result = savant.fetch_bat_tracking(
        year=year, start=short_start.isoformat(), end=as_of.date().isoformat()
    )
    tracking_short: tuple[BatTrackingRow, ...]
    if isinstance(tracking_short_result, FetchFailure):
        diagnostics.append(f"bat tracking (short window): {tracking_short_result.reason}")
        tracking_short = ()
    else:
        tracking_short = tracking_short_result
    tracking_reach_result = savant.fetch_bat_tracking(
        year=year, start=reach_start.isoformat(), end=as_of.date().isoformat()
    )
    tracking_reach: tuple[BatTrackingRow, ...]
    if isinstance(tracking_reach_result, FetchFailure):
        diagnostics.append(f"bat tracking (fallback window): {tracking_reach_result.reason}")
        tracking_reach = ()
    else:
        tracking_reach = tracking_reach_result

    # The fetch window spans the matchup window (D-088), the longest read on
    # the board; form still slices its own L7/L14 reaches out of it.
    window_start = (as_of - timedelta(days=MATCHUP_WINDOW_DAYS)).date()
    days = tuple(window_start + timedelta(days=offset) for offset in range(MATCHUP_WINDOW_DAYS + 1))
    slate_batters = set(all_batter_ids)
    slate_pitchers = set(probable_ids)
    events, event_diagnostics = fetch_window_events(
        fetch_day_events,
        days=days,
        keep=lambda event: event.batter_id in slate_batters or event.pitcher_id in slate_pitchers,
    )
    diagnostics.extend(event_diagnostics)
    form_source_available = len(event_diagnostics) < len(days)
    events_by_batter: dict[int, list[PitchEvent]] = {}
    events_by_pitcher: dict[int, list[PitchEvent]] = {}
    for event in events:
        events_by_batter.setdefault(event.batter_id, []).append(event)
        events_by_pitcher.setdefault(event.pitcher_id, []).append(event)
    short_cutoff = short_start.isoformat()
    reach_cutoff = reach_start.isoformat()

    capture = SourceCaptureId(f"gmf-006-board-{slate.official_date}-{as_of.isoformat()}")
    season_start = _season_window_start(slate_date)

    games: list[GameCard] = []
    for game in slate.games:
        venue = _team_venue(game.venue_id, game.home_team)
        venue_type = venue.venue_type if venue is not None else VenueType.OPEN_AIR
        # Retractable roofs take the neutral indoor value: with no roof-state
        # source in v1, treating them as open-air could award a conditions
        # bonus for weather that never reached the field (D-073).
        roofed = venue_type is not VenueType.OPEN_AIR
        temperature = temperature_for(venue) if venue is not None and not roofed else None
        # Wind only reaches the field of an open-air venue; a roofed game
        # carries no wind reading rather than a number that never applied.
        wind = wind_for(venue) if venue is not None and not roofed else None

        factor_left: ParkFactor | None = None
        factor_right: ParkFactor | None = None
        if venue is not None and venue.savant_venue_id is not None:
            per_side = park_factors.get(venue.savant_venue_id, {})
            factor_left = per_side.get(Handedness.LEFT)
            factor_right = per_side.get(Handedness.RIGHT)

        pitcher_cards: dict[str, PitcherCard | None] = {}
        probable_by_side: dict[str, tuple[int, str] | None] = {}
        for side_key, probable in (("home", game.home_probable), ("away", game.away_probable)):
            if probable is None:
                pitcher_cards[side_key] = None
                probable_by_side[side_key] = None
            else:
                pitcher_cards[side_key] = _pitcher_card(
                    probable.player_id,
                    probable.full_name,
                    season_pitching,
                    arsenal_by_pitcher,
                    fallback_arsenal_by_pitcher,
                    year,
                    tuple(events_by_pitcher.get(probable.player_id, ())),
                )
                probable_by_side[side_key] = (probable.player_id, probable.full_name)

        lineups: dict[str, list[BatterCard]] = {"home": [], "away": []}
        for side_key, team in (("home", game.home_team), ("away", game.away_team)):
            opposing = "away" if side_key == "home" else "home"
            opposing_probable = probable_by_side[opposing]
            pitcher_entity: Pitcher | None = None
            pitcher_throws = ""
            matchup_pitcher_rows: tuple[PitchArsenalRow, ...] = ()
            if opposing_probable is not None:
                pitcher_id, pitcher_name = opposing_probable
                season = season_pitching.get(pitcher_id)
                pitcher_throws = season.throws if season else ""
                pitcher_entity = Pitcher(
                    player_id=PlayerId(str(pitcher_id)),
                    full_name=pitcher_name
                    or (season.full_name if season else f"Player {pitcher_id}"),
                    role=PitcherRole.EXPECTED_STARTER,
                )
                matchup_pitcher_rows = arsenal_by_pitcher.get(pitcher_id, ())

            matchup_cutoff = (as_of - timedelta(days=MATCHUP_WINDOW_DAYS)).date().isoformat()

            for position, player_id in enumerate(lineup_ids[(game.game_pk, team)], start=1):
                line = season_hitting.get(player_id)
                bats = line.bats if line else ""
                player_short = tuple(row for row in tracking_short if row.player_id == player_id)
                player_reach = tuple(row for row in tracking_reach if row.player_id == player_id)
                sides = tuple({row.side for row in player_reach if row.side in ("R", "L")})
                side, _side_reason = resolve_batting_side(bats, sides, pitcher_throws)
                side_short = _side_resolved_tracking(player_short, side)
                side_reach = _side_resolved_tracking(player_reach, side)

                player_events = tuple(events_by_batter.get(player_id, ()))
                # The matchup table's scope: what he has seen from the
                # opposing starter's side over the matchup window (D-088).
                # No probable named → no scope → the table names the absence.
                matchup_scope_events = tuple(
                    event
                    for event in player_events
                    if pitcher_throws
                    and event.pitcher_throws == pitcher_throws
                    and event.game_date >= matchup_cutoff
                )
                recent_events = _recent_window_events(player_events)
                short_events = tuple(
                    event for event in player_events if event.game_date >= short_cutoff
                )
                reach_events = tuple(
                    event for event in player_events if event.game_date >= reach_cutoff
                )
                form = resolve_form_section(
                    aggregate_form(short_events),
                    aggregate_form(reach_events),
                    side_short,
                    side_reach,
                )

                factor = factor_left if side == "L" else factor_right
                # An arsenal-board outage must surface as SOURCE_UNAVAILABLE,
                # not as a derivation over empty rows: matchup stays None so
                # grading records the named source absence (D-070).
                matchup = (
                    MatchupInput(
                        pitcher_rows=matchup_pitcher_rows,
                        batter_rows=arsenal_by_batter.get(player_id, ()),
                        league=league,
                    )
                    if pitcher_entity is not None
                    and batter_arsenal_available
                    and pitcher_arsenal_available
                    else None
                )
                start_utc = _parse_start(game.game_datetime_utc, game.official_date)
                grading_input = BatterGradingInput(
                    game=_game_context(
                        game.game_pk,
                        game.official_date,
                        start_utc,
                        venue,
                        game.venue_id,
                        game.venue_name,
                    ),
                    batter=Batter(
                        player_id=PlayerId(str(player_id)),
                        full_name=line.full_name
                        if line and line.full_name
                        else f"Player {player_id}",
                    ),
                    pitcher=pitcher_entity,
                    pitcher_throws=pitcher_throws,
                    bats=bats,
                    tracking_sides=sides,
                    statcast=statcast.get(player_id),
                    form=form if form_source_available else None,
                    tracking_rows_present=bool(player_reach),
                    matchup=matchup,
                    home_run_factor=factor.factor if factor is not None else None,
                    home_run_factor_plate_appearances=(
                        factor.plate_appearances if factor is not None else 0
                    ),
                    venue_roofed=roofed,
                    temperature_fahrenheit=temperature,
                )
                result = grade_batter(
                    grading_input,
                    config=config,
                    as_of=as_of,
                    season_start=season_start,
                    capture=capture,
                )
                lineups[side_key].append(
                    BatterCard(
                        player_id=player_id,
                        full_name=line.full_name
                        if line and line.full_name
                        else f"Player {player_id}",
                        team=team,
                        bats=bats,
                        batting_side=side,
                        order_position=position,
                        lineup_is_estimate=(game.game_pk, team) in lineup_estimated,
                        season=line,
                        statcast=statcast.get(player_id),
                        form=form,
                        recent_events=recent_events,
                        pitch_lines=_pitch_lines(matchup_scope_events),
                        result=result,
                    )
                )

        games.append(
            GameCard(
                game_pk=game.game_pk,
                status=game.status,
                scheduled_start_utc=_parse_start(game.game_datetime_utc, game.official_date),
                venue_name=game.venue_name,
                venue_type=venue_type,
                home_team=game.home_team,
                away_team=game.away_team,
                home_pitcher=pitcher_cards["home"],
                away_pitcher=pitcher_cards["away"],
                home_batters=tuple(lineups["home"]),
                away_batters=tuple(lineups["away"]),
                temperature_fahrenheit=temperature,
                wind_speed_mph=wind[0] if wind is not None else None,
                wind_direction=wind[1] if wind is not None else None,
                home_run_factor_left=factor_left,
                home_run_factor_right=factor_right,
            )
        )

    return SlateBoard(
        official_date=slate.official_date,
        as_of=as_of,
        games=tuple(games),
        diagnostics=tuple(diagnostics),
    )
