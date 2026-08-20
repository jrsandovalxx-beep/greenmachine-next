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

from collections.abc import Callable
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
    result: EvaluatedGradeResult | NotEvaluableGradeResult


@dataclass(frozen=True)
class PitcherCard:
    """The expected opposing pitcher with season line and qualifying arsenal."""

    player_id: int
    full_name: str
    throws: str
    season: SeasonPitchingLine | None
    arsenal: tuple[PitchArsenalRow, ...]


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
    home_run_factor_left: ParkFactor | None
    home_run_factor_right: ParkFactor | None


@dataclass(frozen=True)
class SlateBoard:
    """The full slate view the four tabs render."""

    official_date: str
    as_of: datetime
    games: tuple[GameCard, ...]
    diagnostics: tuple[str, ...]


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
) -> tuple[tuple[PitchEvent, ...], tuple[str, ...]]:
    """Aggregate per-day event fetches; a failed day is named, not fatal."""
    events: list[PitchEvent] = []
    diagnostics: list[str] = []
    for day in days:
        fetched = fetch_day(day)
        if isinstance(fetched, FetchFailure):
            diagnostics.append(f"pitch events for {day.isoformat()}: {fetched.reason}")
            continue
        events.extend(fetched)
    return tuple(events), tuple(diagnostics)


def _pitcher_card(
    probable_id: int,
    probable_name: str,
    season_pitching: dict[int, SeasonPitchingLine],
    pitcher_arsenal: dict[int, tuple[PitchArsenalRow, ...]],
) -> PitcherCard:
    season = season_pitching.get(probable_id)
    return PitcherCard(
        player_id=probable_id,
        full_name=probable_name or (season.full_name if season else f"Player {probable_id}"),
        throws=season.throws if season else "",
        season=season,
        arsenal=tuple(
            row
            for row in pitcher_arsenal.get(probable_id, ())
            if row.usage_share >= QUALIFYING_USAGE_SHARE
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

    days = tuple(reach_start + timedelta(days=offset) for offset in range(FORM_REACH_DAYS + 1))
    events, event_diagnostics = fetch_window_events(fetch_day_events, days=days)
    diagnostics.extend(event_diagnostics)
    form_source_available = len(event_diagnostics) < len(days)
    events_by_batter: dict[int, list[PitchEvent]] = {}
    for event in events:
        events_by_batter.setdefault(event.batter_id, []).append(event)
    short_cutoff = short_start.isoformat()

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
                short_events = tuple(
                    event for event in player_events if event.game_date >= short_cutoff
                )
                form = resolve_form_section(
                    aggregate_form(short_events),
                    aggregate_form(player_events),
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
