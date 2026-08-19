"""SYNTHETIC input-contract fixtures (GMF-001 criterion 5).

Every number here is a validation artifact chosen to be obviously wrong for
baseball — the OQ-4 discipline — so no fixture value can ever be mistaken for
a baseball judgment. The builders construct fully valid snapshots and then let
tests drive **every absence state** through every observed field.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from greenmachine.inputs import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    BatterInputs,
    ExitVelocityAverage,
    ExitVelocityReading,
    ExpectedWeightedOnBase,
    Handedness,
    HitDistanceReading,
    InputSnapshot,
    IsolatedPower,
    ManualExportProvenance,
    ParkFactor,
    ParkInputs,
    ParkVenue,
    PitchTypeSplit,
    PlateAppearanceEvent,
    PlateAppearanceLog,
    RoofStatus,
    SnapshotField,
    SourceKind,
    SourceRecord,
    SwingingStrikeRate,
    SwingShare,
    UsageShare,
    VenueType,
    WeatherForecast,
    WhiffRate,
    Window,
    WindowedBatterMetrics,
    WindowedPitchTypeSplits,
)

CAPTURED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

SOURCE_SYNTHETIC = "synthetic-fixture"
SOURCE_EXPORT = "synthetic-manual-export"

SOURCES = (
    SourceRecord(
        source_id=SOURCE_SYNTHETIC,
        kind=SourceKind.SYNTHETIC,
        description="synthetic fixture values - deliberately non-baseball numbers",
    ),
    SourceRecord(
        source_id=SOURCE_EXPORT,
        kind=SourceKind.MANUAL_EXPORT,
        description="synthetic stand-in for a manual export provenance chain",
        provenance=ManualExportProvenance(
            source_url="https://example.invalid/synthetic-export",
            export_date=date(2026, 1, 1),
            row_count=1,
            sha256="0" * 64,
        ),
    ),
)


def present_metrics(window: Window) -> WindowedBatterMetrics:
    return WindowedBatterMetrics(
        window=window,
        barrel_rate=SnapshotField.present(
            BattedBallRate(rate=Decimal("0.999"), batted_ball_events=1), SOURCE_SYNTHETIC
        ),
        exit_velocity=SnapshotField.present(
            ExitVelocityAverage(miles_per_hour=Decimal("1.5"), batted_ball_events=1),
            SOURCE_SYNTHETIC,
        ),
        ideal_attack_angle_share=SnapshotField.present(
            SwingShare(share=Decimal("0.001"), tracked_swings=2), SOURCE_SYNTHETIC
        ),
        pull_air_share=SnapshotField.present(
            AirBallShare(share=Decimal("1"), air_balls=3), SOURCE_SYNTHETIC
        ),
    )


def absent_metrics(window: Window, reason: AbsenceReason) -> WindowedBatterMetrics:
    return WindowedBatterMetrics(
        window=window,
        barrel_rate=SnapshotField.absent(reason, SOURCE_SYNTHETIC),
        exit_velocity=SnapshotField.absent(reason, SOURCE_SYNTHETIC),
        ideal_attack_angle_share=SnapshotField.absent(reason, SOURCE_SYNTHETIC),
        pull_air_share=SnapshotField.absent(reason, SOURCE_SYNTHETIC),
    )


def complete_windows(*given: WindowedBatterMetrics) -> tuple[WindowedBatterMetrics, ...]:
    """Totality helper: the contract requires every named window, so the named
    windows not overridden by the caller are filled as absent NOT_YET_OBSERVED.
    Duplicates among ``given`` are passed through untouched, so rejection tests
    still reach the constructor's own check."""
    provided = {metrics.window for metrics in given}
    return given + tuple(
        absent_metrics(window, AbsenceReason.NOT_YET_OBSERVED)
        for window in Window
        if window not in provided
    )


def make_event(event_date: date = date(2026, 1, 1), tracked: bool = True) -> PlateAppearanceEvent:
    """A contact plate appearance (batted ball), tracked or untracked."""
    if tracked:
        exit_velocity = SnapshotField.present(
            ExitVelocityReading(miles_per_hour=Decimal("1.5")), SOURCE_SYNTHETIC
        )
        hit_distance = SnapshotField.present(
            HitDistanceReading(feet=Decimal("9999")), SOURCE_SYNTHETIC
        )
    else:
        exit_velocity = SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_SYNTHETIC)
        hit_distance = SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_SYNTHETIC)
    return PlateAppearanceEvent(
        event_date=event_date,
        pitch_type="ZZ",
        result="synthetic_result",
        batted_ball=True,
        exit_velocity=exit_velocity,
        hit_distance=hit_distance,
    )


def make_non_contact_event(
    event_date: date = date(2026, 1, 3), result: str = "synthetic_strikeout"
) -> PlateAppearanceEvent:
    """A non-contact plate appearance: NOT_APPLICABLE measurements on an
    ordinary row - the trichotomy as everyday data, not an edge case."""
    return PlateAppearanceEvent(
        event_date=event_date,
        pitch_type="ZZ",
        result=result,
        batted_ball=False,
        exit_velocity=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE),
        hit_distance=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE),
    )


def make_log(
    events: tuple[PlateAppearanceEvent, ...] | None = None, window: Window = Window.RECENT_7D
) -> PlateAppearanceLog:
    if events is None:
        events = (
            make_event(date(2026, 1, 1)),
            make_event(date(2026, 1, 2), tracked=False),
            make_non_contact_event(date(2026, 1, 3)),
        )
    return PlateAppearanceLog(window=window, events=events)


def present_split(
    pitch_type: str = "ZZ",
    share: Decimal = Decimal("0.5"),
    sample_pitches: int = 4,
) -> PitchTypeSplit:
    """All seven metrics present: a qualifying, fully available pitch type.

    Every number is an OQ-4 validation artifact — an ISO of 2.998 and an xwOBA
    of 3.997 are impossible in baseball and legal in the contract, which is the
    point: they exercise the bound without ever reading as a judgment.
    """
    return PitchTypeSplit(
        pitch_type=pitch_type,
        usage_share=SnapshotField.present(
            UsageShare(share=share, sample_pitches=sample_pitches), SOURCE_EXPORT
        ),
        barrel_rate=SnapshotField.present(
            BattedBallRate(rate=Decimal("0.999"), batted_ball_events=1), SOURCE_EXPORT
        ),
        exit_velocity=SnapshotField.present(
            ExitVelocityAverage(miles_per_hour=Decimal("1.5"), batted_ball_events=1),
            SOURCE_EXPORT,
        ),
        isolated_power=SnapshotField.present(
            IsolatedPower(points=Decimal("2.998"), at_bats=1), SOURCE_EXPORT
        ),
        expected_woba=SnapshotField.present(
            ExpectedWeightedOnBase(value=Decimal("3.997"), plate_appearances=1), SOURCE_EXPORT
        ),
        whiff_rate=SnapshotField.present(WhiffRate(rate=Decimal("0.001"), swings=2), SOURCE_EXPORT),
        swinging_strike_rate=SnapshotField.present(
            SwingingStrikeRate(rate=Decimal("0.002"), pitches=3), SOURCE_EXPORT
        ),
    )


def split_with_absent_metrics(
    pitch_type: str = "ZZ",
    reason: AbsenceReason = AbsenceReason.NOT_YET_OBSERVED,
    share: Decimal = Decimal("0.5"),
    sample_pitches: int = 4,
) -> PitchTypeSplit:
    """Usage observed, every metric a named absence.

    The healthy-source, nothing-accumulated state, encoded correctly: the usage
    share is a present observation over a positive sample, and a rate over zero
    events is a NAMED ABSENCE — never a constructed zero-denominator value.
    It is also the case that proves availability cannot reach eligibility: this
    pitch type qualifies on usage alone, with nothing to show in any column.
    """
    return PitchTypeSplit(
        pitch_type=pitch_type,
        usage_share=SnapshotField.present(
            UsageShare(share=share, sample_pitches=sample_pitches), SOURCE_EXPORT
        ),
        barrel_rate=SnapshotField.absent(reason, SOURCE_EXPORT),
        exit_velocity=SnapshotField.absent(reason, SOURCE_EXPORT),
        isolated_power=SnapshotField.absent(reason, SOURCE_EXPORT),
        expected_woba=SnapshotField.absent(reason, SOURCE_EXPORT),
        whiff_rate=SnapshotField.absent(reason, SOURCE_EXPORT),
        swinging_strike_rate=SnapshotField.absent(reason, SOURCE_EXPORT),
    )


def split_with_absent_usage(
    pitch_type: str = "ZZ",
    reason: AbsenceReason = AbsenceReason.SOURCE_UNAVAILABLE,
) -> PitchTypeSplit:
    """Usage itself absent, every metric present.

    Eligibility is *unevaluable* here — not "below threshold", which would be a
    claim about a share nobody measured. The metrics are deliberately present:
    a fixture where both were absent could not tell the two questions apart.
    """
    metrics = present_split(pitch_type=pitch_type)
    return PitchTypeSplit(
        pitch_type=pitch_type,
        usage_share=SnapshotField.absent(reason, SOURCE_EXPORT),
        barrel_rate=metrics.barrel_rate,
        exit_velocity=metrics.exit_velocity,
        isolated_power=metrics.isolated_power,
        expected_woba=metrics.expected_woba,
        whiff_rate=metrics.whiff_rate,
        swinging_strike_rate=metrics.swinging_strike_rate,
    )


def fully_absent_split(
    pitch_type: str = "ZZ",
    reason: AbsenceReason = AbsenceReason.SOURCE_UNAVAILABLE,
    source_id: str = SOURCE_EXPORT,
) -> PitchTypeSplit:
    """Every field absent, usage included, all naming one source.

    The shape a split takes when the source supplying its *values* failed but
    the pitch type was still enumerable — so the row exists and has nothing in
    it. Distinct from the split set itself being absent, where no row exists at
    all to have fields."""
    return PitchTypeSplit(
        pitch_type=pitch_type,
        usage_share=SnapshotField.absent(reason, source_id),
        barrel_rate=SnapshotField.absent(reason, source_id),
        exit_velocity=SnapshotField.absent(reason, source_id),
        isolated_power=SnapshotField.absent(reason, source_id),
        expected_woba=SnapshotField.absent(reason, source_id),
        whiff_rate=SnapshotField.absent(reason, source_id),
        swinging_strike_rate=SnapshotField.absent(reason, source_id),
    )


def windowed_splits(
    window: Window,
    splits: tuple[PitchTypeSplit, ...] = (),
    source_id: str = SOURCE_EXPORT,
) -> WindowedPitchTypeSplits:
    """A window's split set, present. An empty tuple is a *present, empty*
    observation — the source answered and this batter faced no tracked pitches
    in the window — and is not the same thing as the set being absent.

    ``source_id`` names whichever source enumerated the pitch types, which need
    not be the source that supplied the metrics inside them: fields carry their
    own provenance, so one snapshot can hold a healthy enumeration and a failed
    metric export at the same time."""
    return WindowedPitchTypeSplits(window=window, splits=SnapshotField.present(splits, source_id))


def absent_windowed_splits(
    window: Window, reason: AbsenceReason, source_id: str = SOURCE_EXPORT
) -> WindowedPitchTypeSplits:
    """A window whose split set is absent, with the reason named: the window
    was never captured, or the source failed. Never an empty tuple, which would
    make an uncaptured window indistinguishable from a batter who faced
    nothing."""
    return WindowedPitchTypeSplits(window=window, splits=SnapshotField.absent(reason, source_id))


def complete_split_windows(
    *given: WindowedPitchTypeSplits,
) -> tuple[WindowedPitchTypeSplits, ...]:
    """Totality helper, mirroring ``complete_windows``: the contract requires a
    split entry for every named window, so windows the caller did not supply are
    filled as an absent set naming NOT_YET_OBSERVED. Duplicates among ``given``
    pass through untouched, so rejection tests still reach the constructor."""
    provided = {windowed.window for windowed in given}
    return given + tuple(
        absent_windowed_splits(window, AbsenceReason.NOT_YET_OBSERVED)
        for window in Window
        if window not in provided
    )


def make_batter(
    batter_id: str = "synthetic-batter-1",
    windows: tuple[WindowedBatterMetrics, ...] | None = None,
    splits: tuple[WindowedPitchTypeSplits, ...] | None = None,
    log: SnapshotField[PlateAppearanceLog] | None = None,
) -> BatterInputs:
    windows = (
        complete_windows(*windows)
        if windows is not None
        else complete_windows(present_metrics(Window.RECENT_7D))
    )
    splits = (
        complete_split_windows(*splits)
        if splits is not None
        else complete_split_windows(
            windowed_splits(Window.SEASON_TO_DATE, (split_with_absent_metrics(),))
        )
    )
    if log is None:
        log = SnapshotField.present(make_log(), SOURCE_SYNTHETIC)
    return BatterInputs(
        batter_id=batter_id,
        name="Synthetic Batter",
        windows=windows,
        pitch_type_splits=splits,
        plate_appearance_log=log,
    )


OPEN_AIR_VENUE = ParkVenue(
    "synthetic-open",
    "Synthetic Open Park",
    "Synthetic Club",
    VenueType.OPEN_AIR,
    None,
    latitude=Decimal("1.000"),
    longitude=Decimal("2.000"),
)
RETRACTABLE_VENUE = ParkVenue(
    "synthetic-retractable",
    "Synthetic Dome",
    "Synthetic Dome Club",
    VenueType.RETRACTABLE_ROOF,
    None,
    latitude=Decimal("3.000"),
    longitude=Decimal("4.000"),
)
FIXED_VENUE = ParkVenue(
    "synthetic-fixed",
    "Synthetic Fixed Dome",
    "Synthetic Fixed Club",
    VenueType.FIXED_ROOF,
    None,
    latitude=Decimal("5.000"),
    longitude=Decimal("6.000"),
)


def make_park(
    venue: ParkVenue = OPEN_AIR_VENUE,
    factor_reason: AbsenceReason | None = None,
    forecast_reason: AbsenceReason | None = AbsenceReason.SOURCE_UNAVAILABLE,
) -> ParkInputs:
    if factor_reason is None:
        lhb = SnapshotField.present(
            ParkFactor(factor=Decimal("999"), handedness=Handedness.LEFT, plate_appearances=1),
            SOURCE_EXPORT,
        )
        rhb = SnapshotField.present(
            ParkFactor(factor=Decimal("1"), handedness=Handedness.RIGHT, plate_appearances=2),
            SOURCE_EXPORT,
        )
    else:
        lhb = SnapshotField.absent(factor_reason, SOURCE_EXPORT)
        rhb = SnapshotField.absent(factor_reason, SOURCE_EXPORT)
    if forecast_reason is None:
        forecast = SnapshotField.present(
            WeatherForecast(
                temperature_f=Decimal("999"),
                wind_speed_mph=Decimal("0"),
                wind_direction="XX",
                short_forecast="synthetic",
                obtained_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            ),
            SOURCE_SYNTHETIC,
        )
    else:
        forecast = SnapshotField.absent(forecast_reason, SOURCE_SYNTHETIC)
    roof: SnapshotField[RoofStatus]
    if venue.venue_type is VenueType.RETRACTABLE_ROOF:
        roof = SnapshotField.present(RoofStatus.UNKNOWN, SOURCE_SYNTHETIC)
    else:
        roof = SnapshotField.absent(AbsenceReason.NOT_APPLICABLE)
    return ParkInputs(
        venue=venue,
        park_factor_lhb=lhb,
        park_factor_rhb=rhb,
        roof_status=roof,
        forecast=forecast,
    )


def make_snapshot(
    batters: tuple[BatterInputs, ...] | None = None,
    parks: tuple[ParkInputs, ...] | None = None,
) -> InputSnapshot:
    return InputSnapshot(
        captured_at=CAPTURED_AT,
        sources=SOURCES,
        batters=batters if batters is not None else (make_batter(),),
        parks=parks if parks is not None else (make_park(),),
    )
