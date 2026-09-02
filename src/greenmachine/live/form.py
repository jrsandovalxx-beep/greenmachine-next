"""Recent-form aggregation from per-pitch events (D-068, D-071).

``aggregate_form`` turns a window of :class:`~greenmachine.live.savant.PitchEvent`
rows into raw form metrics for one batter. It owns only *definitions* (what a
batted ball is, what an air ball is, what a pull is); every sample floor and
every bucket boundary lives in the grading config, per the threshold-table
architecture rule.

``resolve_form_section`` then applies the D-068 per-metric L7 to L14 fallback:
each metric independently prefers the 7-day sample and falls back to the
14-day one when the 7-day sample is empty (never "because the value looks
bad"). Sufficiency against the floors is reported per metric; insufficient
samples stay visible with their marker.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from greenmachine.live.savant import BatTrackingRow, PitchEvent

AIR_BALL_TYPES = frozenset({"fly_ball", "line_drive", "popup"})
BARREL_CLASSIFICATION = 6  # launch_speed_angle band the source labels as barrel
HARD_HIT_THRESHOLD_MPH = Decimal("95")

# Spray-angle geometry: the source's hit-coordinate frame places home plate
# here; pull is signed by batter side, mirroring the public spray charts.
_HOME_PLATE_X = Decimal("125.42")
_HOME_PLATE_DEPTH_Y = Decimal("198.27")

MIN_BBE_FORM = 15
# v2.2 (D-114): the air-ball floor splits by window — L7 gets the lighter
# short-window floor, 15 over L14 and longer. D-133 (PO) lowers the L7
# floor to 5: 8 still read INSUFFICIENT on too many everyday regulars —
# a light week is 5-9 air balls, and 5 keeps the read honest (roughly
# three games' worth) without leaving the window dark. Supersedes part
# of D-068/D-114, append-only.
MIN_AIR_BALLS_FORM_L7 = 5
MIN_AIR_BALLS_FORM = 15
MIN_COMPETITIVE_SWINGS_FORM = 25

# Tracking-board column names, lifted so no call site mixes a tracked-metric
# label with a window suffix on one line (the threshold-table guard reads
# that shape as a hardcoded bucket).
_FIELD_AVERAGE_BAT_SPEED = "avg_bat_speed"


# Plate-appearance event semantics (D-144): which PA-ending events are not
# at-bats, and each hit's total bases. One definition — the form section's
# AB/H counts and the grid's AVG/SLG denominators can never drift apart.
# D-148 (PO audit): intent_walk joined the family after the live cross-check
# against the official game logs found intentional walks charged as at-bats
# (81 of them across four 2025 seasons) — an intentional walk is a walk. The
# sacrifice double-plays ride along unobserved in ~17k scanned pitches but
# unambiguous: a sacrifice is never an at-bat, with or without the runner.
NON_AT_BAT_EVENTS = frozenset(
    {
        "walk",
        "intent_walk",
        "hit_by_pitch",
        "sac_fly",
        "sac_bunt",
        "sac_fly_double_play",
        "sac_bunt_double_play",
        "catcher_interf",
    }
)
HIT_BASES = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
# D-148: a truncated PA (the inning or game ended on the bases with the
# plate appearance unresolved) is no plate appearance at all on the
# official line — verified live: the event-derived PA count ran exactly the
# truncated count above the statsapi season line. It leaves the PA
# denominator entirely rather than riding the non-AB set.
NON_PLATE_APPEARANCE_EVENTS = frozenset({"truncated_pa"})
# D-148: a strikeout with a runner doubled off is still a strikeout on the
# official line (four across four 2025 seasons) — the K reads count it.
STRIKEOUT_EVENTS = frozenset({"strikeout", "strikeout_double_play"})


@dataclass(frozen=True)
class FormMetrics:
    """Raw observed form over one window; rates are PERCENT-scale values."""

    batted_ball_events: int
    barrels: int
    barrel_pct: Decimal | None  # per batted ball, percent scale
    exit_velocity_avg: Decimal | None
    hard_hit_pct: Decimal | None  # per batted ball, percent scale
    air_balls: int
    pull_air_balls: int
    pull_air_pct: Decimal | None  # per air ball, percent scale
    oppo_air_balls: int = 0
    oppo_air_pct: Decimal | None = None  # per air ball, percent scale
    # v2.2 (D-116): barrels hit to the pull side — a raw count, never a
    # rate (a regular averages ~1 barrel a week; 0 in a week is neutral).
    pulled_barrels: int = 0
    # D-144 (PO): the window's volume counts (plate appearances, at-bats,
    # hits) and the all-contact pull read — pulled measurable contacts over
    # measurable contacts, the air reads' measurability widened past the
    # air-ball filter. Percent scale, None when the denominator is empty.
    plate_appearances: int = 0
    at_bats: int = 0
    hits: int = 0
    measurable_contacts: int = 0
    pulled_contacts: int = 0
    pull_pct: Decimal | None = None


def is_measurable_air(event: PitchEvent) -> bool:
    """Whether one classified contact is an air ball with a measurable spray:
    coordinates present and the batter's side known. This is Pull Air %'s
    denominator in both the form section and the matchup grid line — one
    definition, so the two surfaces cannot drift apart."""
    return (
        event.bb_type in AIR_BALL_TYPES
        and event.hc_x is not None
        and event.hc_y is not None
        and event.batter_side in ("L", "R")
    )


def is_measurable_contact(event: PitchEvent) -> bool:
    """Whether one batted ball has a measurable spray: coordinates present
    and the batter's side known — the air reads' measurability without the
    air-ball filter. Pull %'s denominator (D-144, PO)."""
    return event.hc_x is not None and event.hc_y is not None and event.batter_side in ("L", "R")


def is_pull(event: PitchEvent) -> bool:
    """Whether one measurable contact went to the batter's pull side
    (D-071's signed spray convention, D-144's all-contact scope)."""
    spray = _spray_degrees(event)
    if spray is None:
        return False
    return (event.batter_side == "R" and spray > 0) or (event.batter_side == "L" and spray < 0)


def _spray_degrees(event: PitchEvent) -> float | None:
    """The signed spray angle of one contact (D-071's convention: positive
    toward a right-hander's pull side), or None when the contact is not
    measurable. The one geometry pull and oppo share, so the two mirrors
    can never drift apart."""
    if not is_measurable_contact(event):
        return None
    assert event.hc_x is not None and event.hc_y is not None  # the guard just checked both
    return math.degrees(
        math.atan2(
            float(event.hc_x - _HOME_PLATE_X),
            float(_HOME_PLATE_DEPTH_Y - event.hc_y),
        )
    )


def is_pull_air(event: PitchEvent) -> bool:
    """Whether one batted ball is a pulled air ball (D-071's signed spray
    convention): air-ball contact whose spray angle points to the batter's
    pull side. Unmeasurable coordinates or an unknown side read as not-pull
    rather than inventing a direction."""
    return event.bb_type in AIR_BALL_TYPES and is_pull(event)


def is_oppo_air(event: PitchEvent) -> bool:
    """Whether one batted ball is an opposite-field air ball (SP-1): the
    exact mirror of the pull test over the identical measurable-air
    denominator. Spray exactly 0 is neither pull nor oppo — a dead-center
    ball claims no direction."""
    if event.bb_type not in AIR_BALL_TYPES:
        return False
    spray = _spray_degrees(event)
    if spray is None:
        return False
    return (event.batter_side == "R" and spray < 0) or (event.batter_side == "L" and spray > 0)


# D-128 (PO): the straight-away bucket's half-width — Statcast's attack-
# direction convention (pull / straight / oppo split at fifteen degrees).
STRAIGHT_AIR_SPRAY_DEGREES = 15


def is_straight_air(event: PitchEvent) -> bool:
    """Whether one air ball was hit straight away (D-128, PO): the spray
    angle within fifteen degrees of dead center, over the identical
    measurable-air denominator pull and oppo share. The pull and oppo
    reads keep D-071's ratified SIGNED convention (they partition the
    set), so a ball just off center reads as both straight and its signed
    side — the three shares are one denominator, not a partition, and
    the straight hover says so."""
    if event.bb_type not in AIR_BALL_TYPES:
        return False
    spray = _spray_degrees(event)
    if spray is None:
        return False
    return abs(spray) <= STRAIGHT_AIR_SPRAY_DEGREES


def _pct(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) * Decimal(100)) / Decimal(denominator)


def aggregate_form(events: tuple[PitchEvent, ...]) -> FormMetrics:
    """Aggregate one batter's window of pitches into form metrics.

    A pitch counts as a batted-ball event when the source classified its
    contact (``launch_speed_angle`` non-null); fouls arrive unclassified and
    are excluded from BBE denominators by construction.
    """
    bbe = [event for event in events if event.launch_speed_angle is not None]
    barrels = sum(1 for event in bbe if event.launch_speed_angle == BARREL_CLASSIFICATION)
    speeds = [event.launch_speed for event in bbe if event.launch_speed is not None]
    hard_hits = sum(1 for speed in speeds if speed >= HARD_HIT_THRESHOLD_MPH)
    # is_pull_air is False for every unmeasurable contact, so counting pulls
    # over the measurable denominator is the same count with the numerator and
    # denominator visibly drawn from one list.
    measurable_air = [event for event in bbe if is_measurable_air(event)]
    pulls = sum(1 for event in measurable_air if is_pull_air(event))
    oppos = sum(1 for event in measurable_air if is_oppo_air(event))
    pulled_barrels = sum(
        1
        for event in measurable_air
        if is_pull_air(event) and event.launch_speed_angle == BARREL_CLASSIFICATION
    )
    # D-144 (PO): the window's volume counts — PA-ending events, at-bats
    # (PA-ending less walks, hit by pitches, sacrifices, interference) and
    # hits — and the all-contact pull read over the measurable contacts.
    ending = [
        event for event in events if event.event and event.event not in NON_PLATE_APPEARANCE_EVENTS
    ]
    measurable = [event for event in bbe if is_measurable_contact(event)]
    pulled = sum(1 for event in measurable if is_pull(event))
    ev_avg: Decimal | None = None
    if speeds:
        ev_avg = sum(speeds) / Decimal(len(speeds))
    return FormMetrics(
        plate_appearances=len(ending),
        at_bats=sum(1 for event in ending if event.event not in NON_AT_BAT_EVENTS),
        hits=sum(1 for event in ending if event.event in HIT_BASES),
        batted_ball_events=len(bbe),
        barrels=barrels,
        barrel_pct=_pct(barrels, len(bbe)),
        exit_velocity_avg=ev_avg,
        hard_hit_pct=_pct(hard_hits, len(bbe)),
        air_balls=len(measurable_air),
        pull_air_balls=pulls,
        pull_air_pct=_pct(pulls, len(measurable_air)),
        oppo_air_balls=oppos,
        oppo_air_pct=_pct(oppos, len(measurable_air)),
        pulled_barrels=pulled_barrels,
        measurable_contacts=len(measurable),
        pulled_contacts=pulled,
        pull_pct=_pct(pulled, len(measurable)),
    )


@dataclass(frozen=True)
class FormValue:
    """One resolved form metric with its sample and window provenance —
    the window is the batter's last 7 or 14 PLAYED games (D-163, PO)."""

    value: Decimal | None
    sample: int
    window_games: int
    sufficient: bool


@dataclass(frozen=True)
class FormSection:
    """The form metrics after L7/L14 (last 7 / last 14 played games —
    D-163, PO) resolution, all nullable.

    xwOBA left the popup under D-102 — it stays on the Matchups main
    tables, whose grid lines carry it. SP-1 (D-109) amended the D-068 set:
    Oppo Air % mirrors Pull Air % over the identical denominator. SwSp%
    graded from the start until D-174 (PO) retired it: the season-long
    threshold review found it carries almost no home-run signal."""

    barrel_pct: FormValue
    exit_velocity: FormValue
    hard_hit_pct: FormValue
    pull_air_pct: FormValue
    attack_angle_degrees: FormValue
    ideal_attack_angle_pct: FormValue
    bat_speed_mph: FormValue
    oppo_air_pct: FormValue | None = None
    # v2.2 (D-116): pulled barrels as a raw count, never a rate — the value
    # is the count, the sample is the chosen window's BBE. A regular
    # averages ~1 barrel a week, so 0 is a real observation, not a cold
    # streak; None only when neither window holds a measurable air ball.
    pulled_barrels: FormValue | None = None
    # D-144 (PO): the window's volume counts (the value is the count, the
    # sample the window's plate appearances — a count carries no sample
    # floor) and the all-contact pull read. None names the absence (no
    # plate appearance at either reach for the counts, no measurable
    # contact for the pull share).
    at_bats: FormValue | None = None
    hits: FormValue | None = None
    pull_pct: FormValue | None = None


def _pick(
    value_l7: Decimal | None,
    sample_l7: int,
    value_l14: Decimal | None,
    sample_l14: int,
    floor: int,
    floor_l7: int | None = None,
) -> FormValue:
    """Per-metric window resolution: prefer L7, fall back to L14 on empty
    (the batter's last 7, then his last 14, PLAYED games — D-163, PO).

    ``floor`` binds the L14 window; ``floor_l7`` binds the L7 window where
    v2.2 ratified a lighter short-window floor (air balls: 5 at L7 per
    D-133, 15 at L14+) — it defaults to ``floor`` for every other metric."""
    short_floor = floor if floor_l7 is None else floor_l7
    if sample_l7 > 0 and value_l7 is not None:
        return FormValue(
            value=value_l7, sample=sample_l7, window_games=7, sufficient=sample_l7 >= short_floor
        )
    if sample_l14 > 0 and value_l14 is not None:
        return FormValue(
            value=value_l14, sample=sample_l14, window_games=14, sufficient=sample_l14 >= floor
        )
    return FormValue(
        value=value_l7 if value_l7 is not None else value_l14,
        sample=max(sample_l7, sample_l14),
        window_games=7 if sample_l7 >= sample_l14 else 14,
        sufficient=False,
    )


def _pulled_barrels(recent: FormMetrics, extended: FormMetrics) -> FormValue:
    """The pulled-barrel count's window resolution (v2.2, D-116): the L7
    count when the L7 window holds a measurable air ball, else the L14
    count, else a named absence. A raw count carries no sample floor —
    the BBE sample rides beside it and 0 is a real observation."""
    if recent.air_balls > 0:
        return FormValue(
            value=Decimal(recent.pulled_barrels),
            sample=recent.batted_ball_events,
            window_games=7,
            sufficient=True,
        )
    if extended.air_balls > 0:
        return FormValue(
            value=Decimal(extended.pulled_barrels),
            sample=extended.batted_ball_events,
            window_games=14,
            sufficient=True,
        )
    return FormValue(value=None, sample=0, window_games=7, sufficient=False)


def _window_count(count_l7: int, count_l14: int, pa_l7: int, pa_l14: int) -> FormValue | None:
    """A raw window count's L7/L14 resolution (D-144): the L7 count when
    the L7 window holds a plate appearance, else the L14 count, else None.
    A count carries no sample floor — 0 is a real observation of a played
    window (0 hits in a 20-AB week says something; no PA says nothing)."""
    if pa_l7 > 0:
        return FormValue(value=Decimal(count_l7), sample=pa_l7, window_games=7, sufficient=True)
    if pa_l14 > 0:
        return FormValue(value=Decimal(count_l14), sample=pa_l14, window_games=14, sufficient=True)
    return None


def _tracking_value(
    rows_recent: tuple[BatTrackingRow, ...],
    rows_extended: tuple[BatTrackingRow, ...],
    field: str,
) -> tuple[Decimal | None, int, Decimal | None, int]:
    def extract(rows: tuple[BatTrackingRow, ...]) -> tuple[Decimal | None, int]:
        if not rows:
            return None, 0
        swings = sum(row.competitive_swings for row in rows)
        if swings <= 0:
            return None, 0
        weighted = sum(getattr(row, field) * Decimal(row.competitive_swings) for row in rows)
        return weighted / Decimal(swings), swings

    value_recent, sample_recent = extract(rows_recent)
    value_extended, sample_extended = extract(rows_extended)
    return value_recent, sample_recent, value_extended, sample_extended


def resolve_form_section(
    recent: FormMetrics,
    extended: FormMetrics,
    recent_tracking: tuple[BatTrackingRow, ...],
    extended_tracking: tuple[BatTrackingRow, ...],
) -> FormSection:
    """Resolve the form metrics with per-metric L7 to L14 fallback (D-144
    added the volume counts and the all-contact pull read)."""
    aa_value_recent, aa_sample_recent, aa_value_extended, aa_sample_extended = _tracking_value(
        recent_tracking, extended_tracking, "attack_angle"
    )
    iaa_value_recent, iaa_sample_recent, iaa_value_extended, iaa_sample_extended = _tracking_value(
        recent_tracking, extended_tracking, "ideal_attack_angle_share"
    )
    bs_value_recent, bs_sample_recent, bs_value_extended, bs_sample_extended = _tracking_value(
        recent_tracking, extended_tracking, _FIELD_AVERAGE_BAT_SPEED
    )
    iaa = _pick(
        iaa_value_recent,
        iaa_sample_recent,
        iaa_value_extended,
        iaa_sample_extended,
        MIN_COMPETITIVE_SWINGS_FORM,
    )
    return FormSection(
        barrel_pct=_pick(
            recent.barrel_pct,
            recent.batted_ball_events,
            extended.barrel_pct,
            extended.batted_ball_events,
            MIN_BBE_FORM,
        ),
        exit_velocity=_pick(
            recent.exit_velocity_avg,
            recent.batted_ball_events,
            extended.exit_velocity_avg,
            extended.batted_ball_events,
            MIN_BBE_FORM,
        ),
        hard_hit_pct=_pick(
            recent.hard_hit_pct,
            recent.batted_ball_events,
            extended.hard_hit_pct,
            extended.batted_ball_events,
            MIN_BBE_FORM,
        ),
        pull_air_pct=_pick(
            recent.pull_air_pct,
            recent.air_balls,
            extended.pull_air_pct,
            extended.air_balls,
            MIN_AIR_BALLS_FORM,
            floor_l7=MIN_AIR_BALLS_FORM_L7,
        ),
        oppo_air_pct=_pick(
            recent.oppo_air_pct,
            recent.air_balls,
            extended.oppo_air_pct,
            extended.air_balls,
            MIN_AIR_BALLS_FORM,
            floor_l7=MIN_AIR_BALLS_FORM_L7,
        ),
        attack_angle_degrees=_pick(
            aa_value_recent,
            aa_sample_recent,
            aa_value_extended,
            aa_sample_extended,
            MIN_COMPETITIVE_SWINGS_FORM,
        ),
        ideal_attack_angle_pct=FormValue(
            value=iaa.value * Decimal(100) if iaa.value is not None else None,
            sample=iaa.sample,
            window_games=iaa.window_games,
            sufficient=iaa.sufficient,
        ),
        bat_speed_mph=_pick(
            bs_value_recent,
            bs_sample_recent,
            bs_value_extended,
            bs_sample_extended,
            MIN_COMPETITIVE_SWINGS_FORM,
        ),
        pulled_barrels=_pulled_barrels(recent, extended),
        at_bats=_window_count(
            recent.at_bats, extended.at_bats, recent.plate_appearances, extended.plate_appearances
        ),
        hits=_window_count(
            recent.hits, extended.hits, recent.plate_appearances, extended.plate_appearances
        ),
        pull_pct=_pick(
            recent.pull_pct,
            recent.measurable_contacts,
            extended.pull_pct,
            extended.measurable_contacts,
            MIN_BBE_FORM,
        ),
    )
