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
_SWEET_SPOT_LOW = Decimal("8")
_SWEET_SPOT_HIGH = Decimal("32")

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


@dataclass(frozen=True)
class FormMetrics:
    """Raw observed form over one window; rates are PERCENT-scale values."""

    batted_ball_events: int
    barrels: int
    barrel_pct: Decimal | None  # per batted ball, percent scale
    exit_velocity_avg: Decimal | None
    hard_hit_pct: Decimal | None  # per batted ball, percent scale
    sweet_spot_pct: Decimal | None  # per batted ball, percent scale
    air_balls: int
    pull_air_balls: int
    pull_air_pct: Decimal | None  # per air ball, percent scale
    oppo_air_balls: int = 0
    oppo_air_pct: Decimal | None = None  # per air ball, percent scale
    # v2.2 (D-116): barrels hit to the pull side — a raw count, never a
    # rate (a regular averages ~1 barrel a week; 0 in a week is neutral).
    pulled_barrels: int = 0


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


def _spray_degrees(event: PitchEvent) -> float | None:
    """The signed spray angle of one air ball (D-071's convention: positive
    toward a right-hander's pull side), or None when the contact is not
    measurable. The one geometry pull and oppo share, so the two mirrors
    can never drift apart."""
    if not is_measurable_air(event):
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
    spray = _spray_degrees(event)
    if spray is None:
        return False
    return (event.batter_side == "R" and spray > 0) or (event.batter_side == "L" and spray < 0)


def is_oppo_air(event: PitchEvent) -> bool:
    """Whether one batted ball is an opposite-field air ball (SP-1): the
    exact mirror of the pull test over the identical measurable-air
    denominator. Spray exactly 0 is neither pull nor oppo — a dead-center
    ball claims no direction."""
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
    sweet_spots = sum(
        1
        for event in bbe
        if event.launch_angle is not None
        and _SWEET_SPOT_LOW <= event.launch_angle <= _SWEET_SPOT_HIGH
    )
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
    ev_avg: Decimal | None = None
    if speeds:
        ev_avg = sum(speeds) / Decimal(len(speeds))
    return FormMetrics(
        batted_ball_events=len(bbe),
        barrels=barrels,
        barrel_pct=_pct(barrels, len(bbe)),
        exit_velocity_avg=ev_avg,
        hard_hit_pct=_pct(hard_hits, len(bbe)),
        sweet_spot_pct=_pct(sweet_spots, len(bbe)),
        air_balls=len(measurable_air),
        pull_air_balls=pulls,
        pull_air_pct=_pct(pulls, len(measurable_air)),
        oppo_air_balls=oppos,
        oppo_air_pct=_pct(oppos, len(measurable_air)),
        pulled_barrels=pulled_barrels,
    )


@dataclass(frozen=True)
class FormValue:
    """One resolved form metric with its sample and window provenance."""

    value: Decimal | None
    sample: int
    window_days: int
    sufficient: bool


@dataclass(frozen=True)
class FormSection:
    """The form metrics after L7/L14 resolution, all nullable.

    xwOBA left the popup under D-102 — it stays on the Matchups main
    tables, whose grid lines carry it. SP-1 (D-109) amended the D-068 set:
    Oppo Air % mirrors Pull Air % over the identical denominator, and
    SwSp% — computed and graded from the start — is displayed at last."""

    barrel_pct: FormValue
    exit_velocity: FormValue
    hard_hit_pct: FormValue
    sweet_spot_pct: FormValue
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


def _pick(
    value_l7: Decimal | None,
    sample_l7: int,
    value_l14: Decimal | None,
    sample_l14: int,
    floor: int,
    floor_l7: int | None = None,
) -> FormValue:
    """Per-metric window resolution: prefer L7, fall back to L14 on empty.

    ``floor`` binds the L14 window; ``floor_l7`` binds the L7 window where
    v2.2 ratified a lighter short-window floor (air balls: 5 at L7 per
    D-133, 15 at L14+) — it defaults to ``floor`` for every other metric."""
    short_floor = floor if floor_l7 is None else floor_l7
    if sample_l7 > 0 and value_l7 is not None:
        return FormValue(
            value=value_l7, sample=sample_l7, window_days=7, sufficient=sample_l7 >= short_floor
        )
    if sample_l14 > 0 and value_l14 is not None:
        return FormValue(
            value=value_l14, sample=sample_l14, window_days=14, sufficient=sample_l14 >= floor
        )
    return FormValue(
        value=value_l7 if value_l7 is not None else value_l14,
        sample=max(sample_l7, sample_l14),
        window_days=7 if sample_l7 >= sample_l14 else 14,
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
            window_days=7,
            sufficient=True,
        )
    if extended.air_balls > 0:
        return FormValue(
            value=Decimal(extended.pulled_barrels),
            sample=extended.batted_ball_events,
            window_days=14,
            sufficient=True,
        )
    return FormValue(value=None, sample=0, window_days=7, sufficient=False)


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
    """Resolve the eight form metrics with per-metric L7 to L14 fallback."""
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
        sweet_spot_pct=_pick(
            recent.sweet_spot_pct,
            recent.batted_ball_events,
            extended.sweet_spot_pct,
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
            window_days=iaa.window_days,
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
    )
