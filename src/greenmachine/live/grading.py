"""Grading assembly: live data in, one scored snapshot per batter out (GM-041).

This module owns the mapping from fetched rows to the domain's observation
records. It invents no thresholds: every sample floor and bucket boundary is
read from the supplied :class:`GreenMachineConfig`. The only numbers fixed
here are *derivation definitions* (what "pitch mix pressure" means, what a
roofed venue's neutral conditions are), each logged as a decision record.

Provisional v1 derivations (D-073, all marked provisional pending the open
product questions Q15/Q16):

- pitch mix pressure: of the expected starter's qualifying pitch types
  (14% mix share over the named matchup window, D-079), the usage-weighted
  share where the batter's windowed expected wOBA against that pitch meets
  or beats the league's PA-weighted season expected wOBA against that same
  pitch (the baseline is per pitch type, so fastball-heavy pitchers are not
  systematically easier to score against).
- put-away pitch exploitation: on the starter's qualifying pitch type with
  the highest put-away rate, how far the batter's whiff share sits below the
  league's pitch-weighted whiff share, clamped at zero (a batter who whiffs
  *more* than league scores zero, never negative).
- a venue with a fixed roof grades at a neutral indoor temperature instead
  of a forecast; open-air and retractable venues use the live forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from greenmachine.config.schema import ComponentConfig, GreenMachineConfig
from greenmachine.domain.entities import Batter, GameContext, Pitcher
from greenmachine.domain.enums import (
    AcquisitionMethod,
    ComponentId,
    CoverageStatus,
    MeasurementId,
    MissingReason,
    PitcherRole,
    ProviderId,
    SampleStatus,
    SampleType,
    WindowProfile,
)
from greenmachine.domain.grade_result import EvaluatedGradeResult, NotEvaluableGradeResult
from greenmachine.domain.observations import MetricObservation, MissingObservation
from greenmachine.domain.values import (
    CoverageWindow,
    DataCoverage,
    PlayerId,
    SourceCaptureId,
)
from greenmachine.evaluation.serialization import freeze_input_snapshot
from greenmachine.live.form import FormSection, FormValue
from greenmachine.live.savant import PitchArsenalRow, StatcastBatterRow
from greenmachine.scoring.engine import score_snapshot

QUALIFYING_USAGE_SHARE = Decimal("0.15")
# The matchup mix's qualifying bar (D-079) — distinct from the arsenal
# board's 15% qualifying share, which D-070 ratified for the season surface.
MIX_USAGE_SHARE = Decimal("0.14")
ROOFED_VENUE_NEUTRAL_FAHRENHEIT = Decimal("72")
FORM_FALLBACK_REACH_DAYS = 14
PERCENT = Decimal(100)

_UNKNOWN_STARTER_NAME = "Expected starter not announced"


@dataclass(frozen=True)
class LeaguePitchBaseline:
    """League-wide per-pitch-type baselines for the matchup derivations.

    ``expected_woba`` is PA-weighted across batters; ``whiff_share`` is
    pitch-weighted across pitchers. Expected wOBA rather than raw wOBA: at
    per-pitch-type sample sizes the raw figure is dominated by sequencing
    and defense, which the estimator strips out (Q15 review, D-073).
    """

    expected_woba: Decimal
    whiff_share: Decimal
    plate_appearances: int
    pitches: int


@dataclass
class _BaselineSum:
    """Mutable accumulator for the league baselines (weighted sums)."""

    woba_weighted: Decimal = Decimal(0)
    plate_appearances: int = 0
    whiff_weighted: Decimal = Decimal(0)
    pitches: int = 0


@dataclass(frozen=True)
class PitchMixRow:
    """The opposing starter's mix membership for the matchup grade (D-079).

    ``pitches`` and ``usage_share`` come from the window actually used — the
    rolling 30 days, the D-081 L45 reach, or the season board; the surface
    names which. ``put_away_share`` is always the season board's: pitch
    events carry no put-away counts. A None put-away means the season board
    has no row for the pitch type, and the derivation skips the pitch rather
    than inventing a zero.
    """

    pitch_type: str
    pitch_name: str
    pitches: int
    usage_share: Decimal
    put_away_share: Decimal | None


@dataclass(frozen=True)
class BatterPitchLine:
    """The batter's per-pitch line against the starter's side over the
    matchup window (D-079/D-088) — the batter half of the matchup grade.
    Rates are None where their denominator is empty; the derivations skip a
    pitch they cannot read rather than inventing a zero."""

    pitch_type: str
    pitches: int
    expected_woba: Decimal | None
    whiff_share: Decimal | None


@dataclass(frozen=True)
class MatchupInput:
    """Everything the matchup derivations read: both sides plus baselines.

    The pitcher side is the starter's mix over the named window (D-079); the
    batter side is his windowed per-pitch lines against the starter's side.
    The league baselines stay season-long."""

    pitcher_rows: tuple[PitchMixRow, ...]
    batter_rows: tuple[BatterPitchLine, ...]
    league: dict[str, LeaguePitchBaseline]


@dataclass(frozen=True)
class DerivedMatchup:
    """One derived matchup value, or the reason none could be derived."""

    value: Decimal | None
    sample: int
    reason: MissingReason | None


@dataclass(frozen=True)
class BatterGradingInput:
    """All grading inputs for one batter in one game, already fetched."""

    game: GameContext
    batter: Batter
    pitcher: Pitcher | None
    pitcher_throws: str
    bats: str
    tracking_sides: tuple[str, ...]
    statcast: StatcastBatterRow | None
    form: FormSection | None
    tracking_rows_present: bool
    matchup: MatchupInput | None
    home_run_factor: Decimal | None
    home_run_factor_plate_appearances: int
    venue_roofed: bool
    temperature_fahrenheit: Decimal | None


def league_baselines(
    *,
    batter_rows: tuple[PitchArsenalRow, ...],
    pitcher_rows: tuple[PitchArsenalRow, ...],
) -> dict[str, LeaguePitchBaseline]:
    """League baselines per pitch type: PA-weighted wOBA, pitch-weighted whiff."""
    sums: dict[str, _BaselineSum] = {}
    for row in batter_rows:
        entry = sums.setdefault(row.pitch_type, _BaselineSum())
        entry.woba_weighted += row.expected_woba * Decimal(row.plate_appearances)
        entry.plate_appearances += row.plate_appearances
    for row in pitcher_rows:
        entry = sums.setdefault(row.pitch_type, _BaselineSum())
        entry.whiff_weighted += row.whiff_share * Decimal(row.pitches)
        entry.pitches += row.pitches
    baselines: dict[str, LeaguePitchBaseline] = {}
    for pitch_type, entry in sums.items():
        woba = (
            entry.woba_weighted / Decimal(entry.plate_appearances)
            if entry.plate_appearances > 0
            else Decimal(0)
        )
        whiff = entry.whiff_weighted / Decimal(entry.pitches) if entry.pitches > 0 else Decimal(0)
        baselines[pitch_type] = LeaguePitchBaseline(
            expected_woba=woba,
            whiff_share=whiff,
            plate_appearances=entry.plate_appearances,
            pitches=entry.pitches,
        )
    return baselines


def _qualifying_pitcher_rows(matchup: MatchupInput) -> list[PitchMixRow]:
    return [row for row in matchup.pitcher_rows if row.usage_share >= MIX_USAGE_SHARE]


def derive_pitch_mix_pressure(matchup: MatchupInput) -> DerivedMatchup:
    """Usage-weighted share of qualifying pitches the batter hits above league."""
    batter_by_pitch = {row.pitch_type: row for row in matchup.batter_rows}
    weight_total = Decimal(0)
    weight_beaten = Decimal(0)
    sample = 0
    for pitcher_row in _qualifying_pitcher_rows(matchup):
        batter_row = batter_by_pitch.get(pitcher_row.pitch_type)
        league = matchup.league.get(pitcher_row.pitch_type)
        if (
            batter_row is None
            or batter_row.expected_woba is None
            or league is None
            or league.plate_appearances <= 0
        ):
            continue  # a pitch type unreadable on either side leaves both sums
        weight_total += pitcher_row.usage_share
        sample += pitcher_row.pitches
        if batter_row.expected_woba >= league.expected_woba:
            weight_beaten += pitcher_row.usage_share
    if weight_total <= 0:
        return DerivedMatchup(value=None, sample=0, reason=MissingReason.NO_EVENTS_IN_WINDOW)
    return DerivedMatchup(
        value=PERCENT * weight_beaten / weight_total,
        sample=sample,
        reason=None,
    )


def derive_put_away_exploitation(matchup: MatchupInput) -> DerivedMatchup:
    """Whiff suppression vs league on the starter's best put-away pitch."""
    batter_by_pitch = {row.pitch_type: row for row in matchup.batter_rows}
    candidates = sorted(
        (row for row in _qualifying_pitcher_rows(matchup) if row.put_away_share is not None),
        key=lambda row: row.put_away_share or Decimal(0),
        reverse=True,
    )
    for pitcher_row in candidates:
        batter_row = batter_by_pitch.get(pitcher_row.pitch_type)
        league = matchup.league.get(pitcher_row.pitch_type)
        if (
            batter_row is None
            or batter_row.whiff_share is None
            or league is None
            or league.pitches <= 0
        ):
            continue
        if league.whiff_share <= 0:
            continue
        suppression = (league.whiff_share - batter_row.whiff_share) / league.whiff_share
        clamped = max(Decimal(0), min(Decimal(1), suppression))
        return DerivedMatchup(
            value=PERCENT * clamped,
            sample=pitcher_row.pitches,
            reason=None,
        )
    return DerivedMatchup(value=None, sample=0, reason=MissingReason.NO_EVENTS_IN_WINDOW)


def resolve_batting_side(
    bats: str,
    tracking_sides: tuple[str, ...],
    pitcher_throws: str,
) -> tuple[str | None, MissingReason | None]:
    """Resolve the batting side a matchup and park factor apply to (D-065).

    A one-sided batter uses his own side; a switch hitter takes the side
    opposite the expected pitcher's throwing hand. When the side cannot be
    resolved, the handedness-dependent components record a named absence.
    """
    if bats in ("R", "L"):
        return bats, None
    if bats == "S":
        if pitcher_throws == "R":
            return "L", None
        if pitcher_throws == "L":
            return "R", None
        return None, MissingReason.EXPECTED_PITCHER_UNKNOWN
    distinct = {side for side in tracking_sides if side in ("R", "L")}
    if len(distinct) == 1:
        return distinct.pop(), None
    return None, MissingReason.EXPECTED_PITCHER_UNKNOWN


def _component_config(config: GreenMachineConfig, component_id: ComponentId) -> ComponentConfig:
    for component in config.components:
        if component.component_id is component_id:
            return component
    raise KeyError(f"configuration has no component '{component_id.value}'")


def _profile_minimum(config: GreenMachineConfig, component_id: ComponentId) -> int:
    component = _component_config(config, component_id)
    for profile in component.profiles:
        if profile.window_profile is WindowProfile.RECENT_7D:
            return int(profile.minimum_sample_required)
    raise KeyError(f"component '{component_id.value}' configures no RECENT_7D profile")


def _coverage(start: datetime, end: datetime, sample: int) -> DataCoverage:
    window = CoverageWindow(start=start, end=end)
    return DataCoverage(
        requested=window,
        actual=window,
        status=CoverageStatus.COMPLETE,
        source_available=True,
        sample_count=sample,
    )


def _no_coverage(start: datetime, end: datetime, *, source_available: bool) -> DataCoverage:
    return DataCoverage(
        requested=CoverageWindow(start=start, end=end),
        actual=None,
        status=CoverageStatus.NONE,
        source_available=source_available,
        sample_count=0,
    )


def _present(
    *,
    component_id: ComponentId,
    value: Decimal,
    unit: str,
    sample_type: SampleType,
    sample: int,
    minimum: int,
    provider: ProviderId,
    method: AcquisitionMethod,
    measurement_id: MeasurementId | None = None,
    window_start: datetime,
    window_end: datetime,
    as_of: datetime,
    capture: SourceCaptureId,
    coverage_start: datetime,
    coverage_end: datetime,
) -> MetricObservation:
    return MetricObservation(
        component_id=component_id,
        measurement_id=measurement_id,
        window_profile=WindowProfile.RECENT_7D,
        window_start=window_start,
        window_end=window_end,
        as_of=as_of,
        raw_value=value,
        unit=unit,
        sample_type=sample_type,
        sample_count=sample,
        minimum_sample_required=minimum,
        sample_status=(SampleStatus.SUFFICIENT if sample >= minimum else SampleStatus.INSUFFICIENT),
        data_coverage=_coverage(coverage_start, coverage_end, sample),
        provider_id=provider,
        acquisition_method=method,
        source_as_of=as_of,
        retrieved_at=as_of,
        source_capture_id=capture,
    )


def _missing(
    *,
    component_id: ComponentId,
    reason: MissingReason,
    provider: ProviderId | None,
    sample_type: SampleType,
    measurement_id: MeasurementId | None = None,
    window_start: datetime,
    window_end: datetime,
    as_of: datetime,
    capture: SourceCaptureId,
    source_available: bool = True,
) -> MissingObservation:
    return MissingObservation(
        component_id=component_id,
        measurement_id=measurement_id,
        window_profile=WindowProfile.RECENT_7D,
        window_start=window_start,
        window_end=window_end,
        as_of=as_of,
        sample_type=sample_type,
        provider_id=provider,
        source_capture_id=capture,
        missing_reason=reason,
        data_coverage=_no_coverage(window_start, window_end, source_available=source_available),
    )


def _form_observation(
    *,
    component_id: ComponentId,
    form_value: FormValue,
    unit: str,
    empty_reason: MissingReason,
    source_available: bool,
    config: GreenMachineConfig,
    window_start: datetime,
    window_end: datetime,
    as_of: datetime,
    capture: SourceCaptureId,
    measurement_id: MeasurementId | None = None,
) -> MetricObservation | MissingObservation:
    component = _component_config(config, component_id)
    fallback_start = as_of - timedelta(days=FORM_FALLBACK_REACH_DAYS)
    if form_value.value is None or not source_available:
        return _missing(
            component_id=component_id,
            measurement_id=measurement_id,
            reason=empty_reason if source_available else MissingReason.SOURCE_UNAVAILABLE,
            provider=ProviderId.BASEBALL_SAVANT,
            sample_type=component.sample_type,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            source_available=source_available,
        )
    return _present(
        component_id=component_id,
        measurement_id=measurement_id,
        value=form_value.value,
        unit=unit,
        sample_type=component.sample_type,
        sample=form_value.sample,
        minimum=_profile_minimum(config, component_id),
        provider=ProviderId.BASEBALL_SAVANT,
        method=AcquisitionMethod.EVENT_DERIVED,
        window_start=window_start,
        window_end=window_end,
        as_of=as_of,
        capture=capture,
        coverage_start=fallback_start,
        coverage_end=as_of,
    )


def build_batter_observations(
    data: BatterGradingInput,
    *,
    config: GreenMachineConfig,
    as_of: datetime,
    season_start: datetime,
    capture: SourceCaptureId,
) -> tuple[MetricObservation | MissingObservation, ...]:
    """Exactly one observation state per configured component, in config order.

    A component with no usable value becomes a :class:`MissingObservation`
    carrying the named reason — never a zero, never a guessed value.
    """
    window_end = as_of
    window_start = as_of - timedelta(days=7)
    observations: dict[ComponentId, MetricObservation | MissingObservation] = {}

    # --- Power profile: season quality-of-contact board (direct aggregate) ---
    power_rows: tuple[tuple[ComponentId, str, Decimal, int], ...] = ()
    if data.statcast is not None:
        power_rows = (
            (
                ComponentId.EXIT_VELOCITY,
                "mph",
                data.statcast.exit_velocity_avg,
                data.statcast.batted_ball_events,
            ),
            (
                ComponentId.BARREL_PCT,
                "percent",
                data.statcast.barrel_share * PERCENT,
                data.statcast.batted_ball_events,
            ),
            (
                ComponentId.HARD_HIT_PCT,
                "percent",
                data.statcast.hard_hit_share * PERCENT,
                data.statcast.batted_ball_events,
            ),
        )
    for component_id, unit, value, sample in power_rows:
        observations[component_id] = _present(
            component_id=component_id,
            value=value,
            unit=unit,
            sample_type=_component_config(config, component_id).sample_type,
            sample=sample,
            minimum=_profile_minimum(config, component_id),
            provider=ProviderId.BASEBALL_SAVANT,
            method=AcquisitionMethod.DIRECT_AGGREGATE,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            coverage_start=season_start,
            coverage_end=as_of,
        )
    if data.statcast is None:
        for component_id in (
            ComponentId.EXIT_VELOCITY,
            ComponentId.BARREL_PCT,
            ComponentId.HARD_HIT_PCT,
        ):
            observations[component_id] = _missing(
                component_id=component_id,
                reason=MissingReason.PLAYER_NOT_COVERED,
                provider=ProviderId.BASEBALL_SAVANT,
                sample_type=_component_config(config, component_id).sample_type,
                window_start=window_start,
                window_end=window_end,
                as_of=as_of,
                capture=capture,
            )

    # --- Pitcher matchup: derived from arsenal boards ---
    matchup_components = (
        (ComponentId.PITCH_MIX_PRESSURE, derive_pitch_mix_pressure),
        (ComponentId.PUT_AWAY_PITCH_EXPLOITATION, derive_put_away_exploitation),
    )
    for component_id, derive in matchup_components:
        sample_type = _component_config(config, component_id).sample_type
        if data.pitcher is None:
            observations[component_id] = _missing(
                component_id=component_id,
                reason=MissingReason.EXPECTED_PITCHER_UNKNOWN,
                provider=None,
                sample_type=sample_type,
                window_start=window_start,
                window_end=window_end,
                as_of=as_of,
                capture=capture,
            )
            continue
        if data.matchup is None:
            observations[component_id] = _missing(
                component_id=component_id,
                reason=MissingReason.SOURCE_UNAVAILABLE,
                provider=ProviderId.BASEBALL_SAVANT,
                sample_type=sample_type,
                window_start=window_start,
                window_end=window_end,
                as_of=as_of,
                capture=capture,
                source_available=False,
            )
            continue
        derived = derive(data.matchup)
        if derived.reason is not None or derived.value is None:
            observations[component_id] = _missing(
                component_id=component_id,
                reason=derived.reason or MissingReason.NO_EVENTS_IN_WINDOW,
                provider=ProviderId.BASEBALL_SAVANT,
                sample_type=sample_type,
                window_start=window_start,
                window_end=window_end,
                as_of=as_of,
                capture=capture,
            )
            continue
        observations[component_id] = _present(
            component_id=component_id,
            value=derived.value,
            unit="percent",
            sample_type=sample_type,
            sample=derived.sample,
            minimum=_profile_minimum(config, component_id),
            provider=ProviderId.BASEBALL_SAVANT,
            method=AcquisitionMethod.EVENT_DERIVED,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            coverage_start=season_start,
            coverage_end=as_of,
        )

    # --- Form and pull power: event-derived recent windows (D-068) ---
    form = data.form
    form_specs: tuple[tuple[ComponentId, str, MissingReason, MeasurementId | None], ...] = (
        (ComponentId.SWEET_SPOT_PCT, "percent", MissingReason.NO_EVENTS_IN_WINDOW, None),
        (ComponentId.PULL_PCT_AIR_BALLS, "percent", MissingReason.NO_EVENTS_IN_WINDOW, None),
        (
            ComponentId.ATTACK_ANGLE_QUALITY,
            "percent",
            (
                MissingReason.NO_EVENTS_IN_WINDOW
                if data.tracking_rows_present
                else MissingReason.PLAYER_NOT_COVERED
            ),
            MeasurementId.IDEAL_ATTACK_ANGLE_PCT,
        ),
        (
            ComponentId.BAT_SPEED,
            "mph",
            (
                MissingReason.NO_EVENTS_IN_WINDOW
                if data.tracking_rows_present
                else MissingReason.PLAYER_NOT_COVERED
            ),
            None,
        ),
    )
    form_values: dict[ComponentId, FormValue | None] = {
        ComponentId.SWEET_SPOT_PCT: form.sweet_spot_pct if form is not None else None,
        ComponentId.PULL_PCT_AIR_BALLS: form.pull_air_pct if form is not None else None,
        ComponentId.ATTACK_ANGLE_QUALITY: (
            form.ideal_attack_angle_pct if form is not None else None
        ),
        ComponentId.BAT_SPEED: form.bat_speed_mph if form is not None else None,
    }
    for component_id, unit, empty_reason, measurement_id in form_specs:
        form_value = form_values[component_id]
        observations[component_id] = _form_observation(
            component_id=component_id,
            form_value=(
                form_value
                if form_value is not None
                else FormValue(value=None, sample=0, window_days=7, sufficient=False)
            ),
            unit=unit,
            empty_reason=empty_reason,
            source_available=form is not None,
            config=config,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            measurement_id=measurement_id,
        )

    # --- Environment: handedness-matched home-run factor, then conditions ---
    _side, side_reason = resolve_batting_side(data.bats, data.tracking_sides, data.pitcher_throws)
    park_sample_type = _component_config(config, ComponentId.PARK).sample_type
    if side_reason is not None:
        observations[ComponentId.PARK] = _missing(
            component_id=ComponentId.PARK,
            reason=side_reason,
            provider=None,
            sample_type=park_sample_type,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
        )
    elif data.home_run_factor is None:
        observations[ComponentId.PARK] = _missing(
            component_id=ComponentId.PARK,
            reason=MissingReason.SOURCE_UNAVAILABLE,
            provider=ProviderId.BASEBALL_SAVANT,
            sample_type=park_sample_type,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            source_available=False,
        )
    else:
        observations[ComponentId.PARK] = _present(
            component_id=ComponentId.PARK,
            value=data.home_run_factor,
            unit="index",
            sample_type=park_sample_type,
            sample=data.home_run_factor_plate_appearances,
            minimum=_profile_minimum(config, ComponentId.PARK),
            provider=ProviderId.BASEBALL_SAVANT,
            method=AcquisitionMethod.CONFIGURED_PROXY,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            coverage_start=season_start,
            coverage_end=as_of,
        )

    weather_sample_type = _component_config(config, ComponentId.WEATHER).sample_type
    if data.venue_roofed:
        observations[ComponentId.WEATHER] = _present(
            component_id=ComponentId.WEATHER,
            value=ROOFED_VENUE_NEUTRAL_FAHRENHEIT,
            unit="fahrenheit",
            sample_type=weather_sample_type,
            sample=1,
            minimum=_profile_minimum(config, ComponentId.WEATHER),
            provider=ProviderId.NWS,
            method=AcquisitionMethod.CONFIGURED_PROXY,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            coverage_start=window_start,
            coverage_end=window_end,
        )
    elif data.temperature_fahrenheit is not None:
        observations[ComponentId.WEATHER] = _present(
            component_id=ComponentId.WEATHER,
            value=data.temperature_fahrenheit,
            unit="fahrenheit",
            sample_type=weather_sample_type,
            sample=1,
            minimum=_profile_minimum(config, ComponentId.WEATHER),
            provider=ProviderId.NWS,
            method=AcquisitionMethod.DIRECT_AGGREGATE,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            coverage_start=window_start,
            coverage_end=window_end,
        )
    else:
        observations[ComponentId.WEATHER] = _missing(
            component_id=ComponentId.WEATHER,
            reason=MissingReason.WEATHER_UNAVAILABLE,
            provider=ProviderId.NWS,
            sample_type=weather_sample_type,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            capture=capture,
            source_available=False,
        )

    return tuple(observations[component.component_id] for component in config.components)


def grade_batter(
    data: BatterGradingInput,
    *,
    config: GreenMachineConfig,
    as_of: datetime,
    season_start: datetime,
    capture: SourceCaptureId,
) -> EvaluatedGradeResult | NotEvaluableGradeResult:
    """Freeze one batter's inputs into a snapshot and score it (RECENT_7D)."""
    observations = build_batter_observations(
        data, config=config, as_of=as_of, season_start=season_start, capture=capture
    )
    pitcher = data.pitcher
    if pitcher is None:
        pitcher = Pitcher(
            player_id=PlayerId("unannounced"),
            full_name=_UNKNOWN_STARTER_NAME,
            role=PitcherRole.UNCERTAIN,
        )
    present = tuple(o for o in observations if isinstance(o, MetricObservation))
    missing = tuple(o for o in observations if isinstance(o, MissingObservation))
    has_conditions_value = any(o.component_id is ComponentId.WEATHER for o in present)
    snapshot = freeze_input_snapshot(
        source_capture_id=capture,
        game_context=data.game,
        batter=data.batter,
        expected_starting_pitcher=pitcher,
        pitcher_role=pitcher.role,
        as_of=as_of,
        window_profile=WindowProfile.RECENT_7D,
        window_start=as_of - timedelta(days=7),
        window_end=as_of,
        present_observations=present,
        missing_observations=missing,
        validation_inputs=(),
        weather_is_forecast=has_conditions_value,
    )
    return score_snapshot(snapshot, config)
