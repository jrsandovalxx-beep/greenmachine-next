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
    Handedness,
    HitDistanceReading,
    InputSnapshot,
    ManualExportProvenance,
    ParkFactor,
    ParkInputs,
    ParkVenue,
    PitchTypeSplit,
    PlateAppearanceEvent,
    PlateAppearanceLog,
    RoofStatus,
    SnapshotField,
    SourceAvailability,
    SourceKind,
    SourceRecord,
    SwingShare,
    UsageShare,
    VenueType,
    WeatherForecast,
    Window,
    WindowedBatterMetrics,
)

CAPTURED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

SOURCE_SYNTHETIC = "synthetic-fixture"
SOURCE_EXPORT = "synthetic-manual-export"

SOURCES = (
    SourceRecord(
        source_id=SOURCE_SYNTHETIC,
        kind=SourceKind.SYNTHETIC,
        description="synthetic fixture values - deliberately non-baseball numbers",
        availability=SourceAvailability.AVAILABLE,
    ),
    SourceRecord(
        source_id=SOURCE_EXPORT,
        kind=SourceKind.MANUAL_EXPORT,
        description="synthetic stand-in for a manual export provenance chain",
        availability=SourceAvailability.AVAILABLE,
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


def make_batter(
    batter_id: str = "synthetic-batter-1",
    windows: tuple[WindowedBatterMetrics, ...] | None = None,
    splits: tuple[PitchTypeSplit, ...] | None = None,
    log: SnapshotField[PlateAppearanceLog] | None = None,
) -> BatterInputs:
    windows = (
        complete_windows(*windows)
        if windows is not None
        else complete_windows(present_metrics(Window.RECENT_7D))
    )
    if splits is None:
        # The healthy-source, zero-balls-in-play state, encoded correctly: the
        # usage share is a present observation over a positive sample, and the
        # rate over zero batted balls is a NAMED ABSENCE — never a constructed
        # zero-denominator value.
        splits = (
            PitchTypeSplit(
                pitch_type="ZZ",
                usage_share=SnapshotField.present(
                    UsageShare(share=Decimal("0.5"), sample_pitches=4), SOURCE_EXPORT
                ),
                barrel_rate=SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_EXPORT),
                exit_velocity=SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED),
            ),
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
    "synthetic-open", "Synthetic Open Park", "Synthetic Club", VenueType.OPEN_AIR, None
)
RETRACTABLE_VENUE = ParkVenue(
    "synthetic-retractable",
    "Synthetic Dome",
    "Synthetic Dome Club",
    VenueType.RETRACTABLE_ROOF,
    None,
)
FIXED_VENUE = ParkVenue(
    "synthetic-fixed",
    "Synthetic Fixed Dome",
    "Synthetic Fixed Club",
    VenueType.FIXED_ROOF,
    None,
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
