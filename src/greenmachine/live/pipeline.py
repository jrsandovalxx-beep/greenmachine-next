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

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol, TypeVar
from zoneinfo import ZoneInfo

from greenmachine.config.schema import GreenMachineConfig
from greenmachine.domain.entities import Batter, GameContext, Pitcher, Venue
from greenmachine.domain.enums import PitcherRole
from greenmachine.domain.grade_result import EvaluatedGradeResult, NotEvaluableGradeResult
from greenmachine.domain.values import GameId, PlayerId, SourceCaptureId, VenueId
from greenmachine.inputs.contract import Handedness, ParkFactor, ParkVenue, VenueType
from greenmachine.inputs.park_orientation import PARK_ORIENTATION
from greenmachine.inputs.park_reference import PARK_VENUES
from greenmachine.live.form import (
    AIR_BALL_TYPES,
    BARREL_CLASSIFICATION,
    HARD_HIT_THRESHOLD_MPH,
    HIT_BASES,
    NON_AT_BAT_EVENTS,
    FormSection,
    aggregate_form,
    is_measurable_air,
    is_oppo_air,
    is_pull_air,
    is_straight_air,
    resolve_form_section,
)
from greenmachine.live.grading import (
    MIX_USAGE_SHARE,
    QUALIFYING_USAGE_SHARE,
    BatterGradingInput,
    BatterPitchLine,
    MatchupInput,
    PitchMixRow,
    grade_batter,
    league_baselines,
    resolve_batting_side,
)
from greenmachine.live.mlb_api import (
    FetchFailure,
    GameLogEntry,
    MlbStatsApi,
    PitchingLogEntry,
    SeasonHittingLine,
    SeasonPitchingLine,
)
from greenmachine.live.savant import (
    BaseballSavant,
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
from greenmachine.live.wind import wind_from_degrees as _parse_wind_from

FORM_REACH_DAYS = 14
FORM_SHORT_DAYS = 7
# The exit-velocity log lists every pitch from the batter's most recent games
# in the form window, capped at this many games (D-086).
RECENT_EVENT_GAMES_CAP = 7
# The batter's matchup table reads his pitches seen against the
# opposing starter's side over this many days (D-088). D-128 (PO): this
# is the DEFAULT — the Matchups tab's timeframe selector passes its own
# (1-12 weeks or 1-3 months); the season view keeps this one behind the
# grade, which therefore stays the L30 computation there.
MATCHUP_WINDOW_DAYS = 30
# D-128 (PO): the starter's recent-form lines, his per-side usage and
# pitch sets, and his stuff drift all read this many days — the pitcher
# tables' recent-form toggle is the last three months. Season-long PER-SIDE
# mix splits have no published board (the arsenal CSV ignores its hand
# parameter — verified live 2026-08-25), so the event record is the only
# per-side basis and it reaches this far on every build.
# D-128 (PO) set two months; D-142 (PO) rewindows to three.
PITCHER_RECENT_WINDOW_DAYS = 90
# The arsenal breakup's batter half is precomputed at each of these reaches
# (D-106): weeks one through four plus the full month the pitch record
# carries — the dialog's window control selects, never derives. A batter
# window under thirty days caps the list at the window (D-128).
MATCHUP_LINE_WINDOWS_DAYS = (7, 14, 21, 28, 30)
GAME_LOG_LOOKBACK_DAYS = 5
# SP-3 (D-123): the pitching game log's reach. It mirrors the pitcher
# recent window so the start count behind the thin-sample caption is the
# same record the hand splits read. D-142 (PO): pinned to the constant
# itself — D-128 stretched the event record to two months and left this
# at 31 days, so the caption's count silently under-read the record.
PITCHING_LOG_LOOKBACK_DAYS = PITCHER_RECENT_WINDOW_DAYS
# The robbed-HR column (PO 2026-08-24, replacing D-090's +350 ft column):
# batted balls at or past this projected distance that STAYED IN THE PARK
# (a ball that left was not robbed of anything), over the batter's last 7
# days of kept events — homer-shaped contact the HR total hides.
ROBBED_HR_DISTANCE_FLOOR_FT = Decimal("375")
ROBBED_HR_WINDOW_DAYS = 7
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
    # SP-1 (D-109): per-pitch contact shape for the breakup table's batter
    # half — mean exit velocity and the air-ball share of classified contact.
    # batted_balls is the ratified 10-BBE pitch-type floor's basis.
    batted_balls: int = 0
    mean_launch_speed: Decimal | None = None
    air_ball_share: Decimal | None = None
    strikeout_share: Decimal | None = None  # the arsenal board's K% (season scopes)
    # D-124: mean launch angle over the scope's pitches with a measured
    # angle — the window record's per-pitch LA for the breakup's batter
    # half. The arsenal board publishes no per-pitch LA, so season-scope
    # lines leave this None and the pitcher half never shows it.
    mean_launch_angle: Decimal | None = None
    # D-129 (PO): the season breakup's counting columns and air-direction
    # reads — at-bats and hits beside the rates, the raw barrel count, and
    # the pull/oppo shares of measurable air balls (the form section's
    # exact convention, one definition both surfaces share). None where
    # the scope's source publishes no count (the arsenal board publishes
    # none of these).
    at_bats: int | None = None
    hits: int | None = None
    barrel_count: int | None = None
    pull_air_share: Decimal | None = None
    oppo_air_share: Decimal | None = None
    # D-129 (PO): expected ISO — mean expected SLG minus mean expected BA
    # over the scope's batted balls carrying both readings, the per-side
    # xISO the arsenal board cannot split (its hand filter is inert,
    # verified 2026-08-25). None where no batted ball carries both.
    expected_iso: Decimal | None = None


@dataclass(frozen=True)
class RegressionGaps:
    """The season regression gaps (D-110): expected minus actual for ISO and
    wOBA, both sides of each gap read off the same expected-statistics board
    so the denominators match by construction. Computed here, pipeline-side;
    the view only formats (§GMF-008)."""

    xiso_minus_iso: Decimal
    xwoba_minus_woba: Decimal
    plate_appearances: int


def _regression_gaps(row: ExpectedStatsRow | None) -> RegressionGaps | None:
    """Expected minus actual for the season (D-110). xISO is the board's own
    est_slg - est_ba; the actual ISO is its slg - ba — one board, one
    denominator. None when the batter has no row, never an invented zero."""
    if row is None:
        return None
    expected_iso = row.expected_slugging - row.expected_batting_average
    actual_iso = row.slugging - row.batting_average
    return RegressionGaps(
        xiso_minus_iso=expected_iso - actual_iso,
        xwoba_minus_woba=row.xwoba - row.woba,
        plate_appearances=row.plate_appearances,
    )


def _babip(line: SeasonHittingLine | None) -> Decimal | None:
    """BABIP off the season counting line (D-110): (H-HR)/(AB-K-HR+SF).
    None when the line is missing or its denominator is empty — the surface
    names which, never an invented zero."""
    if line is None:
        return None
    denominator = line.at_bats - line.strikeouts - line.home_runs + line.sacrifice_flies
    if denominator <= 0:
        return None
    return Decimal(line.hits - line.home_runs) / Decimal(denominator)


@dataclass(frozen=True)
class BatterGridLine:
    """One row of the matchups grid (D-079): every figure derived here,
    pipeline-side, over a stated scope — the view formats, never derives.
    The L30 row reads the batter's events against the starter's qualifying
    mix pitches; the season row reads the season sources. Rate columns are
    None where their denominator is empty or the scope publishes no count,
    so the surface names the absence instead of inventing a zero."""

    pitches: int
    plate_appearances: int
    at_bats: int
    hits: int
    batted_balls: int | None
    barrels: int | None
    home_runs: int
    exit_velocity: Decimal | None
    barrel_per_pa: Decimal | None
    hard_hit_share: Decimal | None
    batting_average: Decimal | None
    slugging: Decimal | None
    iso: Decimal | None
    # Robbed HRs: 375+ ft balls that stayed in the park over the last 7
    # days of kept events — a different basis from the row's mix scope, so
    # it is computed separately and injected, None when the event record
    # itself failed (never an invented zero).
    robbed_hr_count: int | None
    pull_air_share: Decimal | None
    # SP-1 (D-109): the pull mirror over the identical measurable-air
    # denominator — None on the season view, which publishes no spray read.
    oppo_air_share: Decimal | None = None
    # D-128 (PO): the third air profile — straight-away air balls over the
    # identical measurable-air denominator, so the three shares sum to one.
    # None on the season view like its siblings; a fit read, deliberately
    # uncolored on the grid like oppo.
    straight_air_share: Decimal | None = None
    expected_woba: Decimal | None = None
    whiff_share: Decimal | None = None
    # SP-2 (D-110): the season regression gaps — carried only by the season
    # scope's line; the L30 line leaves this None and the surface omits the
    # columns there.
    gaps: RegressionGaps | None = None
    # D-124: the season Statcast board's average launch angle — season scope
    # only (the L30 mix scope computes no batter-level LA; the dialog reads
    # the window's per-pitch LA). Context, never a firing line: v2.2 reads
    # the share of contact above the HR launch floor, not the average.
    avg_launch_angle: Decimal | None = None


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
    # D-106: the arsenal breakup's batter half, precomputed at each reach in
    # MATCHUP_LINE_WINDOWS_DAYS — one line per pitch in the starter's season
    # arsenal, his usage share, the batter's window figures.
    matchup_lines_by_window: dict[int, tuple[PitchLine, ...]]
    mix_line: BatterGridLine | None
    season_line: BatterGridLine | None
    mix_label: str
    # D-130 (PO): the viewed slate day when he homered on it, else None —
    # the Sluggers tab's neon "$" tag answers "who got the day of the
    # slate I'm looking at", so a slate whose games have not begun tags
    # nobody (supersedes D-094/D-126's last-game-day read, which tagged
    # last night's homer on today's pre-game board). The game log carries
    # only final games, so the tag lands within a board refresh of his
    # game going final. Never a guess: no log, no tag.
    homered_on_slate_day: str | None
    result: EvaluatedGradeResult | NotEvaluableGradeResult
    # SP-1 (D-109): season strikeout share (K/PA) for the high-K tags —
    # computed here, selected by the view.
    season_k_share: Decimal | None = None
    # SP-2 (D-110): the season regression-gap set, BABIP off the counting
    # line, sprint speed, and the contact-first profile inputs (squared-up
    # share of competitive swings and the same board's bat speed) — all
    # computed here, selected by the view.
    season_gaps: RegressionGaps | None = None
    babip: Decimal | None = None
    sprint_speed_fps: Decimal | None = None
    squared_up_share: Decimal | None = None
    squared_up_swings: int = 0
    squared_up_bat_speed: Decimal | None = None


@dataclass(frozen=True)
class PitcherSeasonReads:
    """D-111: the season reads behind the starter header card and the Arms
    tab's starter metrics — each off its named source, None where that
    source has no row for him, never an invented figure. wOBA/xwOBA and
    ISO/xISO read the expected-statistics board against, both sides of each
    pair off the one board so the denominators match; barrel rate and
    launch angle read the Statcast pitcher board (which publishes no
    air-ball split against — season air share stays a named absence; the
    L30 events carry the real split); HR/9 reads the statsapi season line.
    Computed here, pipeline-side — the view only formats (§GMF-008)."""

    plate_appearances: int  # the expected board's PA sample (0 without a row)
    woba: Decimal | None
    expected_woba: Decimal | None
    iso: Decimal | None
    expected_iso: Decimal | None
    batted_ball_events: int  # the Statcast pitcher board's BBE sample (0 without)
    barrel_share: Decimal | None
    avg_launch_angle: Decimal | None
    # D-128 (PO): hard-hit share against off the same Statcast pitcher
    # board (its ev95plus count over its BBE sample) — the pitcher tables
    # carry it on both scopes now.
    hard_hit_share: Decimal | None
    home_runs: int | None  # the season line's HR count (None without a line)
    home_run_per_nine: Decimal | None
    innings_text: str  # the line's baseball-notation innings ("" without one)


@dataclass(frozen=True)
class PitcherRecentLine:
    """D-111: one recent-form scope of the starter's record — overall, or
    against one batting side — computed here from the kept events (§GMF-008:
    the view formats, never derives). D-128 (PO) stretched the scope from
    thirty days to two months; D-142 (PO) rewindows to three. Rates are None where their
    denominator is empty. The event scope publishes no innings, so HR/9
    stays a season read and the HR count shows instead; it publishes no
    per-event expected SLG, so xISO stays a season read — the surface
    names both absences rather than inventing them."""

    plate_appearances: int
    batted_balls: int
    home_runs: int
    woba: Decimal | None
    expected_woba: Decimal | None
    barrel_share: Decimal | None
    avg_launch_angle: Decimal | None
    air_ball_share: Decimal | None
    iso: Decimal | None
    # D-128 (PO): hard-hit share against — 95+ mph batted balls over BBE,
    # the same definition the batter grid carries. The pitcher tables show
    # it on both scopes now.
    hard_hit_share: Decimal | None = None
    # D-114 (v2.2): ground balls over classified BBE — the GB% half of the
    # GB_PROFILE / PITCHER_GAS tags, which the season boards do not publish.
    # The classified count is the share's true denominator (BBE with a
    # bb_type), carried so the tag's sample label never borrows a looser one.
    ground_ball_share: Decimal | None = None
    classified_batted_balls: int = 0


@dataclass(frozen=True)
class StarterWorkload:
    """D-123 (SP-3): the starter's raw workload facts off the pitching game
    log — the last start's pitch count and date, the days since it, the
    most recent starts' counts (newest first), and how many starts the
    window spans. Facts only: v2.2 bars a cap claim unless the team
    announced one, so no limit wording ever rides these numbers. The
    v2.2 firing lines: a last start at or past the workload line is a
    workload flag (a named fact, never a cap), and a window spanning at
    most two starts is the thin sample the hand-split caption names.
    """

    last_start_date: str  # ISO YYYY-MM-DD
    last_start_pitches: int
    days_since_last_start: int
    last_starts: tuple[int, ...]  # newest first, up to three pitch counts
    starts_in_window: int
    workload_flag: bool
    thin_sample: bool


@dataclass(frozen=True)
class StuffDrift:
    """D-123 (SP-3): the primary pitch's season-to-window drift facts —
    the arsenal board's season whiff and usage shares against the same
    figures computed from the kept pitch events. Facts only: the v2.2
    mirage caution ships as this caption alone, no mirage or decay
    wording on screen. The window whiff is None when nobody swung at the
    pitch in the record; a pitcher who never threw it in the window gets
    an honest zero share, never a hidden absence.
    """

    pitch_type: str
    pitch_name: str
    pitches_in_window: int
    usage_season: Decimal
    usage_window: Decimal | None  # None only when the window has no typed pitches
    whiff_season: Decimal
    whiff_window: Decimal | None  # None when the window record holds no swings at it


def _innings_as_decimal(notation: str) -> Decimal | None:
    """MLB's baseball innings notation as a decimal: the fractional digit is
    OUTS (.1/.2), not tenths — "137.1" is 137 and a third innings. Anything
    outside that notation is None: the surface names the absence rather than
    divide by a guessed number."""
    text = notation.strip()
    if not text:
        return None
    whole, dot, fraction = text.partition(".")
    if not whole.isdigit():
        return None
    if not dot:
        return Decimal(whole)
    if len(fraction) != 1 or fraction not in "012":
        return None
    return Decimal(whole) + Decimal(int(fraction)) / Decimal(3)


def _pitcher_season_reads(
    expected_row: ExpectedStatsRow | None,
    statcast_row: StatcastPitcherRow | None,
    season: SeasonPitchingLine | None,
) -> PitcherSeasonReads:
    """The D-111 season reads, each off its named source, None where that
    source has no row — never an invented figure."""
    plate_appearances = 0
    woba: Decimal | None = None
    expected_woba: Decimal | None = None
    iso: Decimal | None = None
    expected_iso: Decimal | None = None
    if expected_row is not None:
        plate_appearances = expected_row.plate_appearances
        woba = expected_row.woba
        expected_woba = expected_row.xwoba
        iso = expected_row.slugging - expected_row.batting_average
        expected_iso = expected_row.expected_slugging - expected_row.expected_batting_average
    batted_ball_events = 0
    barrel_share: Decimal | None = None
    avg_launch_angle: Decimal | None = None
    hard_hit_share: Decimal | None = None
    if statcast_row is not None:
        batted_ball_events = statcast_row.batted_ball_events
        avg_launch_angle = statcast_row.avg_launch_angle
        if batted_ball_events:
            barrel_share = Decimal(statcast_row.barrel_count) / Decimal(batted_ball_events)
            hard_hit_share = Decimal(statcast_row.hard_hit_count) / Decimal(batted_ball_events)
    home_runs: int | None = None
    home_run_per_nine: Decimal | None = None
    innings_text = ""
    if season is not None:
        home_runs = season.home_runs
        innings_text = season.innings_pitched
        innings = _innings_as_decimal(season.innings_pitched)
        if innings is not None and innings > 0:
            home_run_per_nine = Decimal(season.home_runs) * Decimal(9) / innings
    return PitcherSeasonReads(
        plate_appearances=plate_appearances,
        woba=woba,
        expected_woba=expected_woba,
        iso=iso,
        expected_iso=expected_iso,
        batted_ball_events=batted_ball_events,
        barrel_share=barrel_share,
        avg_launch_angle=avg_launch_angle,
        hard_hit_share=hard_hit_share,
        home_runs=home_runs,
        home_run_per_nine=home_run_per_nine,
        innings_text=innings_text,
    )


def _pitcher_recent_line(events: tuple[PitchEvent, ...]) -> PitcherRecentLine | None:
    """One event-record scope of the starter's record off the kept events —
    the last three months (D-142, PO; two months before under D-128,
    L30 before that under D-111), or the full season per batting side off
    his season pitch record (D-143, PO). None when the scope has no events
    at all — the surface names the absence.
    wOBA sums the per-event values over the per-event denominators, the
    same convention the expected-wOBA read uses."""
    if not events:
        return None
    outcomes = _plate_outcomes(events)
    batted = [event for event in events if event.launch_speed is not None]
    barrels = sum(1 for event in batted if event.launch_speed_angle == BARREL_CLASSIFICATION)
    hard_hits = sum(
        1
        for event in batted
        if event.launch_speed is not None and event.launch_speed >= HARD_HIT_THRESHOLD_MPH
    )
    angles = [event.launch_angle for event in events if event.launch_angle is not None]
    woba_total = Decimal(0)
    woba_denominator = Decimal(0)
    for event in events:
        if event.woba_value is None or not event.woba_denom:
            continue
        woba_total += event.woba_value
        woba_denominator += event.woba_denom
    classified = [event for event in batted if event.bb_type]
    air_balls = sum(1 for event in classified if event.bb_type in AIR_BALL_TYPES)
    ground_balls = sum(1 for event in classified if event.bb_type == "ground_ball")
    air_ball_share: Decimal | None = None
    ground_ball_share: Decimal | None = None
    if classified:
        air_ball_share = Decimal(air_balls) / Decimal(len(classified))
        ground_ball_share = Decimal(ground_balls) / Decimal(len(classified))
    return PitcherRecentLine(
        plate_appearances=outcomes.plate_appearances,
        batted_balls=len(batted),
        home_runs=outcomes.home_runs,
        woba=(woba_total / woba_denominator) if woba_denominator else None,
        expected_woba=outcomes.expected_woba,
        barrel_share=(Decimal(barrels) / Decimal(len(batted))) if batted else None,
        avg_launch_angle=(sum(angles, Decimal(0)) / Decimal(len(angles))) if angles else None,
        air_ball_share=air_ball_share,
        iso=outcomes.iso,
        hard_hit_share=(Decimal(hard_hits) / Decimal(len(batted))) if batted else None,
        ground_ball_share=ground_ball_share,
        classified_batted_balls=len(classified),
    )


@dataclass(frozen=True)
class PitcherCard:
    """The expected opposing pitcher: season line, qualifying arsenal, and the
    season-long per-pitch lines the Arsenal table shows (D-087). The arsenal
    figures are season reads with last season filling in when he has no
    current record; the D-111 header-card metrics are season reads off the
    named boards, with L30 companions (overall and per batting side) off the
    window's kept events; the only other window reads are the per-side
    pitch-type set behind the table's side filter and, when that filter is
    on, the per-side usage share it switches to (D-102)."""

    player_id: int
    full_name: str
    throws: str
    season: SeasonPitchingLine | None
    arsenal: tuple[PitchArsenalRow, ...]
    season_lines: tuple[PitchLine, ...]
    season_lines_year: int
    pitches_vs_left: frozenset[str]
    pitches_vs_right: frozenset[str]
    # D-102: each pitch type's share of his pitches to that side over the
    # recent record — the only per-side usage split anywhere, since the
    # arsenal leaderboard publishes usage across all batters only and its
    # hand filter is inert (verified live 2026-08-25). D-128 (PO) stretched
    # the record from thirty days to two months; D-142 (PO) rewindows to
    # three months.
    usage_vs_left: dict[str, Decimal]
    usage_vs_right: dict[str, Decimal]
    # SP-1 (D-109): arsenal-wide whiff — the pitch-weighted mean over his
    # season lines, for the low-whiff side of the high-K interaction tag.
    season_whiff_weighted: Decimal | None = None
    # D-111: the header-card and Arms reads — season figures off the named
    # boards, and the recent-form lines (overall, per batting side) off the
    # kept events — the last three months (D-142, PO; D-128 set two).
    # Each None names its scope's absence.
    season_reads: PitcherSeasonReads | None = None
    recent_overall: PitcherRecentLine | None = None
    recent_vs_left: PitcherRecentLine | None = None
    recent_vs_right: PitcherRecentLine | None = None
    # D-143 (PO): the season-scope per-side splits off his full-season
    # pitch record — the starter card's default side rows now that the
    # toggle flips all three rows. The boards publish no per-side season
    # split, so these are computed from the kept events exactly like the
    # recent lines — HR/9 and xISO stay named absences (no innings and no
    # per-event expected SLG in a pitch record). None names the absence
    # (no fetch wired, fetch failure, or no record).
    season_vs_left: PitcherRecentLine | None = None
    season_vs_right: PitcherRecentLine | None = None
    # SP-3 (D-123): the primary pitch's season-to-window drift facts, and
    # the raw workload facts off the pitching game log. Each None names
    # its absence — no arsenal board rows, or no start in the lookback.
    stuff_drift: StuffDrift | None = None
    workload: StarterWorkload | None = None


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
    # D-111: relative humidity beside the temperature on the conditions
    # surfaces — None for a roofed venue or an unpublished reading, never an
    # invented number.
    relative_humidity_percent: Decimal | None = None
    # SP-4 (D-119): the venue's home-to-center-field axis (degrees true)
    # from PARK_ORIENTATION, and the forecast wind's from-direction parsed
    # to degrees true. Both None for a roofed venue, an unmeasured park, or
    # an unparseable compass reading — the wind tags stay silent rather than
    # resolve against an invented bearing.
    park_orientation_degrees: Decimal | None = None
    wind_from_degrees: Decimal | None = None
    # D-122: the park reference's venue slug, so the conditions surface can
    # join the pinned wind-receptiveness snapshot. None for an unjoined
    # venue — the receptiveness cell then reads as absent, never guessed.
    venue_id: str | None = None


@dataclass(frozen=True)
class SlateBoard:
    """The full slate view the four tabs render."""

    official_date: str
    as_of: datetime
    games: tuple[GameCard, ...]
    diagnostics: tuple[str, ...]


def _homered_on_slate_day(entries: tuple[GameLogEntry, ...], slate_day: str) -> str | None:
    """D-130 (PO): the slate day when he homered on it, else None — the
    neon "$" tags only the day of the slate being viewed, so a pre-game
    board shows no tags at all. The game log carries only final games: an
    in-progress slate day neither tags nor clears. No log, no tag."""
    if any(entry.date == slate_day and entry.home_runs > 0 for entry in entries):
        return slate_day
    return None


def _recent_window_events(events: tuple[PitchEvent, ...]) -> tuple[PitchEvent, ...]:
    """The batter's events from the most recent games in the form window,
    newest game first — the exit-velocity log's rows (D-086). Every pitch of
    a kept game is carried: the pitch mix needs the full counts, and the
    sheet's threshold toggle is a view filter over these rows, not a data
    cut. Source is the same form-window feed the form section reads.
    """
    dates = sorted({event.game_date for event in events}, reverse=True)[:RECENT_EVENT_GAMES_CAP]
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

# D-144 (PO): the PA-ending event semantics (NON_AT_BAT_EVENTS, HIT_BASES)
# live in form.py — the lower layer — so the form section's AB/H counts and
# the grid's AVG/SLG denominators share one definition.
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


@dataclass(frozen=True)
class _PlateOutcomes:
    """The plate-outcome numbers every scoped line derives the same way:
    counts over the scope's PA-ending pitches, whiffs over its swings, each
    rate None where its denominator is empty — the surface names the absence
    rather than inventing a zero. One definition serves the per-pitch lines
    and the whole-scope grid line, so the two can never disagree."""

    plate_appearances: int
    at_bats: int
    hits: int
    home_runs: int
    batting_average: Decimal | None
    slugging: Decimal | None
    iso: Decimal | None
    expected_woba: Decimal | None
    whiff_share: Decimal | None
    # D-129 (PO): the scoped strikeout share and actual wOBA — the season
    # breakup's per-side K% and wOBA, which the arsenal board cannot split
    # by hand (its filter is inert, verified 2026-08-25).
    strikeout_share: Decimal | None = None
    woba: Decimal | None = None


def _plate_outcomes(events: Sequence[PitchEvent]) -> _PlateOutcomes:
    ending = [event for event in events if event.event]
    at_bats = sum(1 for event in ending if event.event not in NON_AT_BAT_EVENTS)
    hits = sum(1 for event in ending if event.event in HIT_BASES)
    bases = sum(HIT_BASES.get(event.event, 0) for event in ending)
    average = Decimal(hits) / Decimal(at_bats) if at_bats else None
    slugging = Decimal(bases) / Decimal(at_bats) if at_bats else None
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
    swings = sum(1 for event in events if event.description in _SWING_DESCRIPTIONS)
    whiffs = sum(1 for event in events if event.description in _WHIFF_DESCRIPTIONS)
    actual_woba_ending = [
        event for event in ending if event.woba_value is not None and event.woba_denom
    ]
    actual_woba_total = sum(
        (event.woba_value for event in actual_woba_ending if event.woba_value is not None),
        Decimal(0),
    )
    actual_woba_denominator = sum(
        (event.woba_denom for event in actual_woba_ending if event.woba_denom is not None),
        Decimal(0),
    )
    strikeouts = sum(1 for event in ending if event.event == "strikeout")
    return _PlateOutcomes(
        plate_appearances=len(ending),
        at_bats=at_bats,
        hits=hits,
        home_runs=sum(1 for event in ending if event.event == "home_run"),
        batting_average=average,
        slugging=slugging,
        iso=(slugging - average if average is not None and slugging is not None else None),
        expected_woba=(woba_total / woba_denominator) if woba_denominator else None,
        whiff_share=Decimal(whiffs) / Decimal(swings) if swings else None,
        strikeout_share=(Decimal(strikeouts) / Decimal(len(ending)) if ending else None),
        woba=((actual_woba_total / actual_woba_denominator) if actual_woba_denominator else None),
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
        outcomes = _plate_outcomes(group)
        batted = [event for event in group if event.launch_speed is not None]
        barrels = sum(1 for event in batted if event.launch_speed_angle == BARREL_CLASSIFICATION)
        hard_hits = sum(
            1
            for event in batted
            if event.launch_speed is not None and event.launch_speed >= HARD_HIT_THRESHOLD_MPH
        )
        # Contact shape (D-109): EV over the pitches with a measured speed,
        # air-ball share over classified contact — the same BBE definition
        # the form section uses.
        bbe = [event for event in group if event.launch_speed_angle is not None]
        air_balls = sum(1 for event in bbe if event.bb_type in AIR_BALL_TYPES)
        mean_speed: Decimal | None = None
        if batted:
            mean_speed = sum(
                (event.launch_speed for event in batted if event.launch_speed is not None),
                Decimal(0),
            ) / Decimal(len(batted))
        # Per-pitch LA (D-124): over the pitches with a measured angle, the
        # same measured-event base EV reads.
        angles = [event.launch_angle for event in group if event.launch_angle is not None]
        mean_angle: Decimal | None = None
        if angles:
            mean_angle = sum(angles, Decimal(0)) / Decimal(len(angles))
        # D-129 (PO): the air-direction reads over the form section's exact
        # measurable-air convention, and the per-side expected ISO off the
        # per-event expected SLG/BA (both readings present, one base).
        measurable_air = [event for event in group if is_measurable_air(event)]
        pulls = sum(1 for event in measurable_air if is_pull_air(event))
        oppos = sum(1 for event in measurable_air if is_oppo_air(event))
        expected_pairs = [
            (event.estimated_slg, event.estimated_ba)
            for event in batted
            if event.estimated_slg is not None and event.estimated_ba is not None
        ]
        expected_iso: Decimal | None = None
        if expected_pairs:
            expected_iso = (
                sum((slg for slg, _ in expected_pairs), Decimal(0)) / Decimal(len(expected_pairs))
            ) - (sum((ba for _, ba in expected_pairs), Decimal(0)) / Decimal(len(expected_pairs)))
        lines.append(
            PitchLine(
                pitch_type=pitch_type,
                pitch_name=_PITCH_NAMES.get(pitch_type, pitch_type),
                pitches=len(group),
                usage_share=Decimal(len(group)) / Decimal(total),
                plate_appearances=outcomes.plate_appearances,
                batting_average=outcomes.batting_average,
                slugging=outcomes.slugging,
                iso=outcomes.iso,
                home_runs=outcomes.home_runs,
                barrel_share=Decimal(barrels) / Decimal(len(batted)) if batted else None,
                hard_hit_share=Decimal(hard_hits) / Decimal(len(batted)) if batted else None,
                expected_woba=outcomes.expected_woba,
                whiff_share=outcomes.whiff_share,
                woba=outcomes.woba,
                strikeout_share=outcomes.strikeout_share,
                batted_balls=len(bbe),
                mean_launch_speed=mean_speed,
                air_ball_share=Decimal(air_balls) / Decimal(len(bbe)) if bbe else None,
                mean_launch_angle=mean_angle,
                at_bats=outcomes.at_bats,
                hits=outcomes.hits,
                barrel_count=barrels if batted else None,
                pull_air_share=(
                    Decimal(pulls) / Decimal(len(measurable_air)) if measurable_air else None
                ),
                oppo_air_share=(
                    Decimal(oppos) / Decimal(len(measurable_air)) if measurable_air else None
                ),
                expected_iso=expected_iso,
            )
        )
    lines.sort(key=lambda line: line.usage_share, reverse=True)
    return tuple(lines)


def season_breakup_lines(
    pitcher_events: Sequence[PitchEvent],
    batter_events: Sequence[PitchEvent],
    *,
    batter_side: str,
    pitcher_throws: str,
    hand_filter: bool,
) -> tuple[tuple[PitchLine, ...], dict[str, PitchLine]]:
    """The dialog's season breakup scopes (D-129, PO): the starter's
    per-pitch lines and the batter's, each off that player's season pitch
    record — his pitches to the batter's side and the batter's pitches
    seen from the starter's hand by default, or both records unfiltered
    when the hand filter is off. Every metric in a row derives from exactly
    one scope, so the two toggle positions can never disagree about their
    denominators (§GMF-008 — the view formats, never filters). Returns his
    lines usage-sorted and the batter's keyed by pitch type."""
    if hand_filter:
        pitcher_scope = [event for event in pitcher_events if event.batter_side == batter_side]
        batter_scope = [event for event in batter_events if event.pitcher_throws == pitcher_throws]
    else:
        pitcher_scope = list(pitcher_events)
        batter_scope = list(batter_events)
    pitcher_lines = _pitch_lines(pitcher_scope)
    batter_lines = {line.pitch_type: line for line in _pitch_lines(batter_scope)}
    return pitcher_lines, batter_lines


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


def _arsenal_whiff_weighted(rows: Sequence[PitchArsenalRow]) -> Decimal | None:
    """Arsenal-wide whiff (D-109): the pitch-weighted mean over a pitcher's
    season arsenal rows — one read of how hard his whole mix is to hit, for
    the low-whiff side of the high-K interaction tag. None when the board
    shows no pitches, never an invented zero."""
    weighed = [row for row in rows if row.pitches > 0]
    total = sum(row.pitches for row in weighed)
    if not total:
        return None
    return sum((row.whiff_share * Decimal(row.pitches) for row in weighed), Decimal(0)) / Decimal(
        total
    )


def _matchup_lines(
    starter_lines: tuple[PitchLine, ...], seen_lines: tuple[PitchLine, ...]
) -> tuple[PitchLine, ...]:
    """The arsenal breakup's batter half (D-106): one line per pitch in the
    starter's season arsenal, in his usage order, carrying HIS usage share —
    the batter's seen-share said what the league throws, never what this
    starter does. The batter's own figures keep their window scope; a pitch
    he has not seen from this side keeps zeroed counts and empty rates, so
    the surface dashes the cells instead of hiding the row.
    """
    by_type = {line.pitch_type: line for line in seen_lines}
    lines: list[PitchLine] = []
    for starter in starter_lines:
        seen = by_type.get(starter.pitch_type)
        if seen is None:
            lines.append(
                PitchLine(
                    pitch_type=starter.pitch_type,
                    pitch_name=starter.pitch_name,
                    pitches=0,
                    usage_share=starter.usage_share,
                    plate_appearances=0,
                    batting_average=None,
                    slugging=None,
                    iso=None,
                    home_runs=None,
                    barrel_share=None,
                    hard_hit_share=None,
                    expected_woba=None,
                    whiff_share=None,
                )
            )
        else:
            lines.append(
                replace(
                    seen,
                    pitch_name=starter.pitch_name or seen.pitch_name,
                    usage_share=starter.usage_share,
                )
            )
    return tuple(lines)


def _robbed_hr_count(events: Sequence[PitchEvent], cutoff: str) -> int:
    """Robbed HRs over the batter's kept events at or after ``cutoff`` —
    projected 375+ feet and STAYED IN THE PARK (the play's result was not
    a home run). A raw count, never a rate: one robbed ball a week is a
    regular's pace, and zero is a real observation, not a cold streak."""
    return sum(
        1
        for event in events
        if event.game_date >= cutoff
        and event.hit_distance is not None
        and event.hit_distance >= ROBBED_HR_DISTANCE_FLOOR_FT
        and event.event != "home_run"
    )


def _batter_grid_line(
    events: Sequence[PitchEvent], *, robbed_count: int | None
) -> BatterGridLine | None:
    """The batter's grid line over one stated scope of pitch events — his
    L30 record against the starter's qualifying mix pitches (D-079). Every
    rate reads exactly these events; a scope with no events returns None so
    the surface states 'no data available' (D-081). The robbed-HR count is
    the one column off a different basis — the batter's whole last-7-days
    event record, not this scope — so it arrives computed (PO 2026-08-24)."""
    if not events:
        return None
    outcomes = _plate_outcomes(events)
    # BBE follows the source's contact classification (as form does), so
    # classified fouls never swell the batted-ball denominators.
    batted = [event for event in events if event.launch_speed_angle is not None]
    speeds = [event.launch_speed for event in batted if event.launch_speed is not None]
    speed_total = sum(speeds, Decimal(0))
    barrels = sum(1 for event in batted if event.launch_speed_angle == BARREL_CLASSIFICATION)
    hard_hits = sum(
        1
        for event in batted
        if event.launch_speed is not None and event.launch_speed >= HARD_HIT_THRESHOLD_MPH
    )
    # Pull Air % mirrors the form section: pulled air balls over measurable
    # air balls — a ball without coordinates or a known side leaves both
    # counts (D-090 keeps it a separate metric from the distance column).
    measurable_air = [event for event in batted if is_measurable_air(event)]
    pulls = sum(1 for event in measurable_air if is_pull_air(event))
    oppos = sum(1 for event in measurable_air if is_oppo_air(event))
    # D-128 (PO): the straight-away bucket over the same denominator. Pull
    # and oppo keep the ratified signed convention, so they partition the
    # set and straight (a fifteen-degree band) overlaps a near-center
    # ball's signed side — one denominator, not a partition.
    straights = sum(1 for event in measurable_air if is_straight_air(event))
    return BatterGridLine(
        pitches=len(events),
        plate_appearances=outcomes.plate_appearances,
        at_bats=outcomes.at_bats,
        hits=outcomes.hits,
        batted_balls=len(batted),
        barrels=barrels,
        home_runs=outcomes.home_runs,
        exit_velocity=(speed_total / Decimal(len(speeds))) if speeds else None,
        barrel_per_pa=(
            Decimal(barrels) / Decimal(outcomes.plate_appearances)
            if outcomes.plate_appearances
            else None
        ),
        hard_hit_share=Decimal(hard_hits) / Decimal(len(batted)) if batted else None,
        batting_average=outcomes.batting_average,
        slugging=outcomes.slugging,
        iso=outcomes.iso,
        robbed_hr_count=robbed_count,
        pull_air_share=(Decimal(pulls) / Decimal(len(measurable_air)) if measurable_air else None),
        oppo_air_share=(Decimal(oppos) / Decimal(len(measurable_air)) if measurable_air else None),
        straight_air_share=(
            Decimal(straights) / Decimal(len(measurable_air)) if measurable_air else None
        ),
        expected_woba=outcomes.expected_woba,
        whiff_share=outcomes.whiff_share,
    )


def _per_air_share(row: BattedBallRow | None, direction: str) -> Decimal | None:
    """One air-direction bucket as a share of the batter's air balls
    (D-128, PO): the batted-ball board's rates are shares of ALL batted
    balls (the three sum to its air share), so each rebases on the air
    share here — pipeline-side, §GMF-008. None without a row or an air
    ball: the surface names the absence, never an invented split."""
    if row is None or not row.air_share:
        return None
    rate = {
        "pull": row.pull_air_share_of_bbe,
        "straight": row.straight_air_share_of_bbe,
        "oppo": row.oppo_air_share_of_bbe,
    }[direction]
    return rate / row.air_share


def _season_grid_line(
    line: SeasonHittingLine | None,
    statcast: StatcastBatterRow | None,
    arsenal_rows: Sequence[PitchArsenalRow],
    gaps: RegressionGaps | None = None,
    robbed_count: int | None = None,
    batted_ball: BattedBallRow | None = None,
) -> BatterGridLine | None:
    """The batter's season-view grid line (D-079's toggle target), composed
    from the season sources: the hitting line for AB/H/HR/AVG/SLG/ISO, the
    statcast board for EV/barrels/hard-hit, the arsenal board for
    PA-weighted xwOBA and pitch-weighted Swing-Str, and — D-128 (PO) —
    the batted-ball profile board for the three air-direction reads:
    Savant's own published pull/straight/oppo buckets, rebased here to
    shares of his air balls (the board's rates are shares of ALL batted
    balls and sum to its air share) so the column speaks one denominator
    on both views. A missing row or an empty air share names the absence,
    never an invented split. D-128 (PO): the robbed-HR count shows on
    the season view too — it arrives computed, always on its own last-7-
    days basis, which the surface names. The D-110 regression gaps ride
    along when the expected-stats board covers him."""
    if line is None and statcast is None and not arsenal_rows and batted_ball is None:
        return None
    at_bats = line.at_bats if line else 0
    hits = line.hits if line else 0
    plate_appearances = line.plate_appearances if line else 0
    average = Decimal(hits) / Decimal(at_bats) if at_bats else None
    slugging = Decimal(line.total_bases) / Decimal(at_bats) if line and at_bats else None
    woba_rows = [row for row in arsenal_rows if row.plate_appearances > 0]
    woba_pa = sum(row.plate_appearances for row in woba_rows)
    woba_total = sum(
        (row.expected_woba * Decimal(row.plate_appearances) for row in woba_rows), Decimal(0)
    )
    whiff_rows = [row for row in arsenal_rows if row.pitches > 0]
    whiff_pitches = sum(row.pitches for row in whiff_rows)
    whiff_total = sum((row.whiff_share * Decimal(row.pitches) for row in whiff_rows), Decimal(0))
    barrels = statcast.barrel_count if statcast else None
    return BatterGridLine(
        pitches=sum(row.pitches for row in arsenal_rows),
        plate_appearances=plate_appearances,
        at_bats=at_bats,
        hits=hits,
        batted_balls=statcast.batted_ball_events if statcast else None,
        barrels=barrels,
        home_runs=line.home_runs if line else 0,
        exit_velocity=statcast.exit_velocity_avg if statcast else None,
        barrel_per_pa=(
            Decimal(barrels) / Decimal(plate_appearances)
            if barrels is not None and plate_appearances
            else None
        ),
        hard_hit_share=statcast.hard_hit_share if statcast else None,
        batting_average=average,
        slugging=slugging,
        iso=(slugging - average if average is not None and slugging is not None else None),
        robbed_hr_count=robbed_count,
        pull_air_share=_per_air_share(batted_ball, "pull"),
        oppo_air_share=_per_air_share(batted_ball, "oppo"),
        straight_air_share=_per_air_share(batted_ball, "straight"),
        expected_woba=(woba_total / Decimal(woba_pa)) if woba_pa else None,
        whiff_share=(whiff_total / Decimal(whiff_pitches)) if whiff_pitches else None,
        gaps=gaps,
        avg_launch_angle=statcast.avg_launch_angle if statcast else None,
    )


def _window_mix_rows(
    window_events: Sequence[PitchEvent],
    board_rows: Sequence[PitchArsenalRow],
) -> tuple[PitchMixRow, ...]:
    """The starter's mix from his pitch events over the record actually
    used (D-079): usage from the event counts, put-away always from the
    season board — events carry no put-away counts. A pitch type absent
    from the board keeps put_away_share None; the derivation skips it
    rather than inventing a zero. Since D-128 (PO) this builder is the
    last resort: the season board is the mix scope, and only a starter
    with no arsenal board at either year reads his three-month record."""
    counts: dict[str, int] = {}
    for event in window_events:
        if event.pitch_type:
            counts[event.pitch_type] = counts.get(event.pitch_type, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return ()
    put_away = {row.pitch_type: row.put_away_share for row in board_rows}
    rows = [
        PitchMixRow(
            pitch_type=pitch_type,
            pitch_name=_PITCH_NAMES.get(pitch_type, pitch_type),
            pitches=count,
            usage_share=Decimal(count) / Decimal(total),
            put_away_share=put_away.get(pitch_type),
        )
        for pitch_type, count in counts.items()
    ]
    rows.sort(key=lambda row: row.usage_share, reverse=True)
    return tuple(rows)


def _board_mix_rows(board_rows: Sequence[PitchArsenalRow]) -> tuple[PitchMixRow, ...]:
    """The starter's mix from a season arsenal board — since D-128 (PO)
    the primary scope, the whole mix for the whole season (current
    season, else last season labelled, D-087)."""
    rows = [
        PitchMixRow(
            pitch_type=row.pitch_type,
            pitch_name=row.pitch_name,
            pitches=row.pitches,
            usage_share=row.usage_share,
            put_away_share=row.put_away_share,
        )
        for row in board_rows
    ]
    rows.sort(key=lambda row: row.usage_share, reverse=True)
    return tuple(rows)


def _chunked(ids: tuple[int, ...], size: int) -> list[tuple[int, ...]]:
    return [ids[index : index + size] for index in range(0, len(ids), size)]


class _HasPlayerId(Protocol):
    @property
    def player_id(self) -> int: ...


_PlayerRow = TypeVar("_PlayerRow", bound=_HasPlayerId)


def _by_player(rows: Iterable[_PlayerRow]) -> dict[int, tuple[_PlayerRow, ...]]:
    """Rows grouped by player id, source order preserved within each player."""
    grouped: dict[int, list[_PlayerRow]] = {}
    for row in rows:
        grouped.setdefault(row.player_id, []).append(row)
    return {player_id: tuple(group) for player_id, group in grouped.items()}


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


# v2.2's workload firing line: a last start at or past this many pitches
# is a workload flag — a named raw fact, never a cap claim (a cap is only
# a cap if the team announced one).
WORKLOAD_FLAG_PITCH_LINE = 100
# v2.2's thin-sample line: a window spanning at most this many starts
# names itself beside the L30 hand splits.
THIN_SAMPLE_STARTS_LINE = 2


def _starter_workload(
    entries: tuple[PitchingLogEntry, ...], slate_date: date
) -> StarterWorkload | None:
    """SP-3 (D-123): the raw workload facts from a pitcher's game log.
    Starts only — a relief outing is not a start — newest first. No start
    in the lookback is a None: the surface names the absence, and the log
    lists completed games only, so today's outing never counts."""
    starts = sorted(
        (entry for entry in entries if entry.started),
        key=lambda entry: (entry.date, entry.game_pk),
        reverse=True,
    )
    if not starts:
        return None
    last = starts[0]
    return StarterWorkload(
        last_start_date=last.date,
        last_start_pitches=last.pitches,
        days_since_last_start=(slate_date - date.fromisoformat(last.date)).days,
        last_starts=tuple(entry.pitches for entry in starts[:3]),
        starts_in_window=len(starts),
        workload_flag=last.pitches >= WORKLOAD_FLAG_PITCH_LINE,
        thin_sample=len(starts) <= THIN_SAMPLE_STARTS_LINE,
    )


def _stuff_drift(
    season_rows: tuple[PitchArsenalRow, ...],
    window_events: tuple[PitchEvent, ...],
) -> StuffDrift | None:
    """SP-3 (D-123): the primary pitch's drift facts — the season arsenal
    board against the same shares computed from the window's kept events.
    The primary pitch is the board's top-usage row; no board rows, no
    drift line. The window usage is an honest zero when he never threw
    the pitch in the record, and the window whiff is None when nobody
    swung at it — the caption names the absence, never a zero."""
    if not season_rows:
        return None
    primary = max(season_rows, key=lambda row: row.usage_share)
    typed = [event for event in window_events if event.pitch_type]
    own = [event for event in typed if event.pitch_type == primary.pitch_type]
    usage_window = Decimal(len(own)) / Decimal(len(typed)) if typed else None
    swings = sum(1 for event in own if event.description in _SWING_DESCRIPTIONS)
    whiffs = sum(1 for event in own if event.description in _WHIFF_DESCRIPTIONS)
    whiff_window = Decimal(whiffs) / Decimal(swings) if swings else None
    return StuffDrift(
        pitch_type=primary.pitch_type,
        pitch_name=primary.pitch_name,
        pitches_in_window=len(own),
        usage_season=primary.usage_share,
        usage_window=usage_window,
        whiff_season=primary.whiff_share,
        whiff_window=whiff_window,
    )


def _side_usage(events: tuple[PitchEvent, ...], side: str) -> dict[str, Decimal]:
    """Each pitch type's share of the pitches he threw to one batting side
    in the window record (D-102). The arsenal leaderboard's usage spans all
    batters; this is the per-hitter-hand basis the side toggle switches to.
    An empty scope is an empty mapping — never an invented share."""
    counts: dict[str, int] = {}
    total = 0
    for event in events:
        if event.batter_side != side or not event.pitch_type:
            continue
        counts[event.pitch_type] = counts.get(event.pitch_type, 0) + 1
        total += 1
    if not total:
        return {}
    return {pitch: Decimal(count) / Decimal(total) for pitch, count in counts.items()}


def _pitcher_card(
    probable_id: int,
    probable_name: str,
    season_pitching: dict[int, SeasonPitchingLine],
    pitcher_arsenal: dict[int, tuple[PitchArsenalRow, ...]],
    fallback_arsenal: dict[int, tuple[PitchArsenalRow, ...]],
    pitcher_expected: dict[int, ExpectedStatsRow],
    pitcher_statcast: dict[int, StatcastPitcherRow],
    season_year: int,
    window_events: tuple[PitchEvent, ...],
    log_entries: tuple[PitchingLogEntry, ...] = (),
    slate_date: date | None = None,
    season_events: tuple[PitchEvent, ...] = (),
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
        usage_vs_left=_side_usage(window_events, "L"),
        usage_vs_right=_side_usage(window_events, "R"),
        season_whiff_weighted=_arsenal_whiff_weighted(season_rows),
        season_reads=_pitcher_season_reads(
            pitcher_expected.get(probable_id),
            pitcher_statcast.get(probable_id),
            season,
        ),
        recent_overall=_pitcher_recent_line(window_events),
        recent_vs_left=_pitcher_recent_line(
            tuple(event for event in window_events if event.batter_side == "L")
        ),
        recent_vs_right=_pitcher_recent_line(
            tuple(event for event in window_events if event.batter_side == "R")
        ),
        season_vs_left=_pitcher_recent_line(
            tuple(event for event in season_events if event.batter_side == "L")
        ),
        season_vs_right=_pitcher_recent_line(
            tuple(event for event in season_events if event.batter_side == "R")
        ),
        stuff_drift=_stuff_drift(season_rows, window_events),
        workload=(_starter_workload(log_entries, slate_date) if slate_date is not None else None),
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
    batter_window_days: int = MATCHUP_WINDOW_DAYS,
    fetch_day_events: Callable[[date], tuple[PitchEvent, ...] | FetchFailure],
    temperature_for: Callable[[ParkVenue, datetime], Decimal | None],
    park_factors: dict[int, dict[Handedness, ParkFactor]],
    wind_for: Callable[[ParkVenue, datetime], tuple[Decimal, str] | None] = lambda venue, at: None,
    humidity_for: Callable[[ParkVenue, datetime], Decimal | None] = lambda venue, at: None,
    fetch_pitcher_season_events: Callable[[int], tuple[PitchEvent, ...] | FetchFailure]
    | None = None,
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
    arsenal_by_pitcher = _by_player(pitcher_arsenal_rows)
    arsenal_by_batter = _by_player(batter_arsenal)

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
            fallback_arsenal_by_pitcher = _by_player(
                row for row in fallback_result if row.player_id in missing_current
            )

    season_hitting: dict[int, SeasonHittingLine] = {}
    for chunk in _chunked(all_batter_ids, SEASON_IDS_PER_REQUEST):
        fetched = api.fetch_season_hitting(chunk)
        if isinstance(fetched, FetchFailure):
            diagnostics.append(f"season hitting: {fetched.reason}")
            continue
        season_hitting.update(fetched)

    # D-100: the money tag reads the near-real-time game log (completed games
    # only), not the day-indexed pitch record — Savant's search CSV can run a
    # day behind, which both missed and mistimed tags. Five days of lookback
    # covers off-days and rest days.
    game_logs: dict[int, tuple[GameLogEntry, ...]] = {}
    log_start = (slate_date - timedelta(days=GAME_LOG_LOOKBACK_DAYS)).strftime("%m/%d/%Y")
    log_end = slate_date.strftime("%m/%d/%Y")
    for chunk in _chunked(all_batter_ids, SEASON_IDS_PER_REQUEST):
        fetched_logs = api.fetch_recent_game_logs(chunk, log_start, log_end)
        if isinstance(fetched_logs, FetchFailure):
            diagnostics.append(f"game logs: {fetched_logs.reason}")
            continue
        game_logs.update(fetched_logs)

    season_pitching: dict[int, SeasonPitchingLine] = {}
    if probable_ids:
        fetched_pitching = api.fetch_season_pitching(probable_ids)
        if isinstance(fetched_pitching, FetchFailure):
            diagnostics.append(f"season pitching: {fetched_pitching.reason}")
        else:
            season_pitching = fetched_pitching

    # SP-3 (D-123): the probables' pitching game logs — the raw workload
    # facts and the start count behind the thin-sample caption. The reach
    # mirrors the pitcher recent window (D-142) so both read the same record.
    pitching_logs: dict[int, tuple[PitchingLogEntry, ...]] = {}
    if probable_ids:
        pitching_log_start = (slate_date - timedelta(days=PITCHING_LOG_LOOKBACK_DAYS)).strftime(
            "%m/%d/%Y"
        )
        for chunk in _chunked(probable_ids, SEASON_IDS_PER_REQUEST):
            fetched_pitching_logs = api.fetch_recent_pitching_logs(
                chunk, pitching_log_start, log_end
            )
            if isinstance(fetched_pitching_logs, FetchFailure):
                diagnostics.append(f"pitching game logs: {fetched_pitching_logs.reason}")
                continue
            pitching_logs.update(fetched_pitching_logs)

    # D-143 (PO): each probable's full-season pitch record — the season
    # scope behind the starter cards' per-side rows, now that the card's
    # toggle flips all three rows. One query per probable (the caller
    # caches per slate day); None when the build wires no fetcher
    # (backtest boards skip it — a fetch per probable per backtest day
    # would bury the range), a failure names itself in diagnostics.
    season_events_by_pitcher: dict[int, tuple[PitchEvent, ...]] = {}
    if fetch_pitcher_season_events is not None:
        for pid in probable_ids:
            fetched_season_events = fetch_pitcher_season_events(pid)
            if isinstance(fetched_season_events, FetchFailure):
                diagnostics.append(
                    f"pitcher season pitch record ({pid}): {fetched_season_events.reason}"
                )
                continue
            season_events_by_pitcher[pid] = fetched_season_events

    statcast_result = savant.fetch_statcast_batters(year=year)
    statcast: dict[int, StatcastBatterRow]
    if isinstance(statcast_result, FetchFailure):
        diagnostics.append(f"statcast board: {statcast_result.reason}")
        statcast = {}
    else:
        statcast = statcast_result
        if not statcast:
            diagnostics.append("statcast board: returned zero rows")

    # D-128 (PO): the season batted-ball profile board — the season view's
    # pull/straight/oppo air reads are Savant's own published numbers, not
    # home-built derivations. One extra CSV per build; degrades to named
    # absences on its own failure.
    batted_ball_result = savant.fetch_batted_ball(year=year)
    batted_ball: dict[int, BattedBallRow]
    if isinstance(batted_ball_result, FetchFailure):
        diagnostics.append(f"batted-ball board: {batted_ball_result.reason}")
        batted_ball = {}
    else:
        batted_ball = batted_ball_result
        if not batted_ball:
            diagnostics.append("batted-ball board: returned zero rows")

    # D-110's three season boards: expected statistics (the regression gaps'
    # only source), sprint speed, and the contact-quality board behind the
    # contact-first profile. Each degrades to a named absence on its own.
    expected_result = savant.fetch_expected_stats(year=year)
    expected_stats: dict[int, ExpectedStatsRow]
    if isinstance(expected_result, FetchFailure):
        diagnostics.append(f"expected-stats board: {expected_result.reason}")
        expected_stats = {}
    else:
        expected_stats = expected_result
        if not expected_stats:
            diagnostics.append("expected-stats board: returned zero rows")
    sprint_result = savant.fetch_sprint_speed(year=year)
    sprint_speed: dict[int, SprintSpeedRow]
    if isinstance(sprint_result, FetchFailure):
        diagnostics.append(f"sprint-speed board: {sprint_result.reason}")
        sprint_speed = {}
    else:
        sprint_speed = sprint_result
        if not sprint_speed:
            diagnostics.append("sprint-speed board: returned zero rows")
    squared_result = savant.fetch_squared_up(year=year)
    squared_up: dict[int, SquaredUpRow]
    if isinstance(squared_result, FetchFailure):
        diagnostics.append(f"squared-up board: {squared_result.reason}")
        squared_up = {}
    else:
        squared_up = squared_result
        if not squared_up:
            diagnostics.append("squared-up board: returned zero rows")

    # D-111's two pitcher boards: expected statistics against (the header
    # card's wOBA/xwOBA and ISO/xISO) and the Statcast board against (barrel
    # rate, launch angle, air/ground split). Each degrades to a named
    # absence on its own.
    pitcher_expected_result = savant.fetch_pitcher_expected_stats(year=year)
    pitcher_expected: dict[int, ExpectedStatsRow]
    if isinstance(pitcher_expected_result, FetchFailure):
        reason = pitcher_expected_result.reason
        diagnostics.append(f"pitcher expected-stats board: {reason}")
        pitcher_expected = {}
    else:
        pitcher_expected = pitcher_expected_result
        if not pitcher_expected:
            diagnostics.append("pitcher expected-stats board: returned zero rows")
    pitcher_statcast_result = savant.fetch_statcast_pitchers(year=year)
    pitcher_statcast: dict[int, StatcastPitcherRow]
    if isinstance(pitcher_statcast_result, FetchFailure):
        diagnostics.append(f"statcast pitcher board: {pitcher_statcast_result.reason}")
        pitcher_statcast = {}
    else:
        pitcher_statcast = pitcher_statcast_result
        if not pitcher_statcast:
            diagnostics.append("statcast pitcher board: returned zero rows")

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
    # Grouped once: the per-batter loop below reads each board hundreds of
    # times, and a full-board scan per batter is quadratic in slate size.
    short_tracking_by_batter = _by_player(tracking_short)
    reach_tracking_by_batter = _by_player(tracking_reach)

    # The event record spans the batter window the Matchups tab selected
    # (D-128, PO — thirty days by default), stretched to the pitcher
    # recent-form reach when that is longer, so one fetch serves the
    # batter grids, the grade, the robbed count, and the starter reads.
    # Form still slices its own L7/L14 reaches out of it.
    if batter_window_days < ROBBED_HR_WINDOW_DAYS:
        raise ValueError(
            f"the batter window ({batter_window_days} days) must at least "
            f"cover the robbed-HR window ({ROBBED_HR_WINDOW_DAYS} days)"
        )
    record_days = max(batter_window_days, PITCHER_RECENT_WINDOW_DAYS)
    window_start = (as_of - timedelta(days=record_days)).date()
    days = tuple(window_start + timedelta(days=offset) for offset in range(record_days + 1))
    slate_batters = set(all_batter_ids)
    slate_pitchers = set(probable_ids)

    def keep_event(event: PitchEvent) -> bool:
        return event.batter_id in slate_batters or event.pitcher_id in slate_pitchers

    events, event_diagnostics = fetch_window_events(
        fetch_day_events,
        days=days,
        keep=keep_event,
    )
    diagnostics.extend(event_diagnostics)
    form_source_available = len(event_diagnostics) < len(days)
    events_by_batter: dict[int, list[PitchEvent]] = {}
    events_by_pitcher: dict[int, list[PitchEvent]] = {}
    for event in events:
        events_by_batter.setdefault(event.batter_id, []).append(event)
        events_by_pitcher.setdefault(event.pitcher_id, []).append(event)
    # The batter scope (grid line, grade leg, robbed count, dialog reaches)
    # reads the selected window; the starter scope (recent-form lines,
    # per-side usage, stuff drift) reads the three-month pitcher reach.
    matchup_cutoff = (as_of - timedelta(days=batter_window_days)).date().isoformat()
    pitcher_cutoff = (as_of - timedelta(days=PITCHER_RECENT_WINDOW_DAYS)).date().isoformat()
    window_cutoffs = {
        reach: (as_of - timedelta(days=reach)).date().isoformat()
        for reach in MATCHUP_LINE_WINDOWS_DAYS
        if reach <= batter_window_days
    }
    if batter_window_days not in window_cutoffs:
        window_cutoffs[batter_window_days] = matchup_cutoff

    # Each probable's mix (D-128, PO): his season arsenal board — the whole
    # mix for the whole season — else last season's board (labelled, D-087),
    # else the three-month event record (the only remaining source). The
    # label names which. D-081's L45 reach is subsumed: the record now
    # spans sixty days on every build, so no second fetch ever fires.
    mix_by_pitcher: dict[int, tuple[PitchMixRow, ...]] = {}
    mix_label_by_pitcher: dict[int, str] = {}
    for pid in probable_ids:
        pitcher_window = tuple(
            event for event in events_by_pitcher.get(pid, ()) if event.game_date >= pitcher_cutoff
        )
        current_board = arsenal_by_pitcher.get(pid, ())
        board_rows = current_board or fallback_arsenal_by_pitcher.get(pid, ())
        if current_board:
            mix_by_pitcher[pid] = _board_mix_rows(current_board)
            mix_label_by_pitcher[pid] = "season"
        elif board_rows:
            mix_by_pitcher[pid] = _board_mix_rows(board_rows)
            mix_label_by_pitcher[pid] = "last season"
        elif pitcher_window:
            mix_by_pitcher[pid] = _window_mix_rows(pitcher_window, ())
            mix_label_by_pitcher[pid] = "last 90 days"
        else:
            mix_by_pitcher[pid] = ()
            mix_label_by_pitcher[pid] = ""
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
        # Game-scoped, batter-invariant: one start instant and one frozen
        # context shared by every card in the game. Computed before the
        # weather reads so each one asks for the forecast covering first
        # pitch rather than the hour the board was built (D-131).
        start_utc = _parse_start(game.game_datetime_utc, game.official_date)
        temperature = (
            temperature_for(venue, start_utc) if venue is not None and not roofed else None
        )
        # Wind only reaches the field of an open-air venue; a roofed game
        # carries no wind reading rather than a number that never applied.
        wind = wind_for(venue, start_utc) if venue is not None and not roofed else None
        # D-111: humidity rides the same rule — a roofed venue's reading
        # never reaches the field.
        humidity = humidity_for(venue, start_utc) if venue is not None and not roofed else None

        factor_left: ParkFactor | None = None
        factor_right: ParkFactor | None = None
        if venue is not None and venue.savant_venue_id is not None:
            per_side = park_factors.get(venue.savant_venue_id, {})
            factor_left = per_side.get(Handedness.LEFT)
            factor_right = per_side.get(Handedness.RIGHT)

        game_context = _game_context(
            game.game_pk,
            game.official_date,
            start_utc,
            venue,
            game.venue_id,
            game.venue_name,
        )

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
                    pitcher_expected,
                    pitcher_statcast,
                    year,
                    # D-128 (PO): the starter's event reads — recent-form
                    # lines, per-side usage and pitch sets, stuff drift —
                    # all read the three-month pitcher record now.
                    tuple(
                        event
                        for event in events_by_pitcher.get(probable.player_id, ())
                        if event.game_date >= pitcher_cutoff
                    ),
                    pitching_logs.get(probable.player_id, ()),
                    slate_date,
                    season_events_by_pitcher.get(probable.player_id, ()),
                )
                probable_by_side[side_key] = (probable.player_id, probable.full_name)

        lineups: dict[str, list[BatterCard]] = {"home": [], "away": []}
        for side_key, team in (("home", game.home_team), ("away", game.away_team)):
            opposing = "away" if side_key == "home" else "home"
            opposing_probable = probable_by_side[opposing]
            opposing_card = pitcher_cards[opposing]
            starter_season_lines = opposing_card.season_lines if opposing_card is not None else ()
            pitcher_entity: Pitcher | None = None
            pitcher_throws = ""
            starter_mix: tuple[PitchMixRow, ...] = ()
            mix_label = ""
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
                starter_mix = mix_by_pitcher.get(pitcher_id, ())
                mix_label = mix_label_by_pitcher.get(pitcher_id, "")
            # The grid scope's mix line (D-079): the starter's qualifying
            # pitch types, one set for every batter on this side.
            qualifying_mix = frozenset(
                row.pitch_type for row in starter_mix if row.usage_share >= MIX_USAGE_SHARE
            )
            lineup_key = (game.game_pk, team)
            lineup_is_estimate = lineup_key in lineup_estimated
            for position, player_id in enumerate(lineup_ids[lineup_key], start=1):
                line = season_hitting.get(player_id)
                bats = line.bats if line else ""
                display_name = line.full_name if line and line.full_name else f"Player {player_id}"
                statcast_row = statcast.get(player_id)
                player_short = short_tracking_by_batter.get(player_id, ())
                player_reach = reach_tracking_by_batter.get(player_id, ())
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
                # D-110's season reads for this batter, resolved once.
                gaps = _regression_gaps(expected_stats.get(player_id))
                sprint_row = sprint_speed.get(player_id)
                squared_row = squared_up.get(player_id)
                # The grid scope (D-079): his L30 events against the
                # starter's qualifying mix pitches, from the starter's side.
                mix_scope_events = tuple(
                    event for event in matchup_scope_events if event.pitch_type in qualifying_mix
                )
                # An arsenal-board outage must surface as SOURCE_UNAVAILABLE,
                # not as a derivation over empty rows: matchup stays None so
                # grading records the named source absence (D-070). The
                # league baselines read both boards, so both must be live.
                matchup = (
                    MatchupInput(
                        pitcher_rows=starter_mix,
                        batter_rows=tuple(
                            BatterPitchLine(
                                pitch_type=pitch_line.pitch_type,
                                pitches=pitch_line.pitches,
                                expected_woba=pitch_line.expected_woba,
                                whiff_share=pitch_line.whiff_share,
                            )
                            for pitch_line in _pitch_lines(mix_scope_events)
                        ),
                        league=league,
                    )
                    if pitcher_entity is not None
                    and batter_arsenal_available
                    and pitcher_arsenal_available
                    else None
                )
                grading_input = BatterGradingInput(
                    game=game_context,
                    batter=Batter(
                        player_id=PlayerId(str(player_id)),
                        full_name=display_name,
                    ),
                    pitcher=pitcher_entity,
                    pitcher_throws=pitcher_throws,
                    bats=bats,
                    tracking_sides=sides,
                    statcast=statcast_row,
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
                # The robbed count reads the batter's whole last-7-days
                # record, not the mix scope — None when the event record
                # itself failed. D-128 (PO): it rides BOTH grid lines, so
                # the season view shows it too — always on the L7 basis,
                # which the surface names.
                robbed_count = (
                    _robbed_hr_count(
                        events_by_batter.get(player_id, ()),
                        window_cutoffs[ROBBED_HR_WINDOW_DAYS],
                    )
                    if form_source_available
                    else None
                )
                lineups[side_key].append(
                    BatterCard(
                        player_id=player_id,
                        full_name=display_name,
                        team=team,
                        bats=bats,
                        batting_side=side,
                        order_position=position,
                        lineup_is_estimate=lineup_is_estimate,
                        season=line,
                        statcast=statcast_row,
                        form=form,
                        recent_events=recent_events,
                        matchup_lines_by_window=(
                            {
                                reach: _matchup_lines(
                                    starter_season_lines,
                                    _pitch_lines(
                                        tuple(
                                            event
                                            for event in matchup_scope_events
                                            if event.game_date >= window_cutoffs[reach]
                                        )
                                    ),
                                )
                                for reach in sorted(window_cutoffs)
                            }
                            if starter_season_lines
                            else {}
                        ),
                        mix_line=(
                            _batter_grid_line(mix_scope_events, robbed_count=robbed_count)
                            if pitcher_entity is not None
                            else None
                        ),
                        season_line=_season_grid_line(
                            line,
                            statcast_row,
                            arsenal_by_batter.get(player_id, ()),
                            gaps,
                            robbed_count=robbed_count,
                            batted_ball=batted_ball.get(player_id),
                        ),
                        mix_label=mix_label,
                        homered_on_slate_day=_homered_on_slate_day(
                            game_logs.get(player_id, ()), slate.official_date
                        ),
                        result=result,
                        season_k_share=(
                            Decimal(line.strikeouts) / Decimal(line.plate_appearances)
                            if line is not None and line.plate_appearances
                            else None
                        ),
                        season_gaps=gaps,
                        babip=_babip(line),
                        sprint_speed_fps=(
                            sprint_row.sprint_speed if sprint_row is not None else None
                        ),
                        squared_up_share=(
                            squared_row.squared_up_per_swing if squared_row is not None else None
                        ),
                        squared_up_swings=(
                            squared_row.competitive_swings if squared_row is not None else 0
                        ),
                        squared_up_bat_speed=(
                            squared_row.avg_bat_speed if squared_row is not None else None
                        ),
                    )
                )

        games.append(
            GameCard(
                game_pk=game.game_pk,
                status=game.status,
                scheduled_start_utc=start_utc,
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
                relative_humidity_percent=humidity,
                # SP-4 (D-119): the park axis and the parsed wind direction.
                # A roofed venue carries neither, matching the wind reading
                # itself; an unmapped venue or an unparseable compass text
                # degrades to None, never a guessed bearing.
                park_orientation_degrees=(
                    PARK_ORIENTATION.get(venue.venue_id)
                    if venue is not None and not roofed
                    else None
                ),
                wind_from_degrees=(_parse_wind_from(wind[1]) if wind is not None else None),
                # D-122: the slug the wind-receptiveness snapshot keys on.
                venue_id=venue.venue_id if venue is not None else None,
            )
        )

    return SlateBoard(
        official_date=slate.official_date,
        as_of=as_of,
        games=tuple(games),
        diagnostics=tuple(diagnostics),
    )
