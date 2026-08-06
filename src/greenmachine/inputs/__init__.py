"""GreenMachine input contract package (GMF-001, FEATURE_PHASE_PLAN §7).

Public surface: the ``InputSnapshot`` contract every screen renders, and the
thirty-venue park reference table, whose venue-type taxonomy follows
decision D-055.
"""

from greenmachine.inputs.contract import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    BatterInputs,
    DisplayState,
    ExitVelocityAverage,
    Handedness,
    InputSnapshot,
    ManualExportProvenance,
    ParkFactor,
    ParkInputs,
    ParkVenue,
    PitchTypeSplit,
    RoofStatus,
    SnapshotField,
    SourceAvailability,
    SourceKind,
    SourceRecord,
    SwingShare,
    VenueType,
    WeatherForecast,
    Window,
    WindowedBatterMetrics,
)
from greenmachine.inputs.errors import InputContractError
from greenmachine.inputs.park_reference import PARK_VENUES

__all__ = [
    "PARK_VENUES",
    "AbsenceReason",
    "AirBallShare",
    "BattedBallRate",
    "BatterInputs",
    "DisplayState",
    "ExitVelocityAverage",
    "Handedness",
    "InputContractError",
    "InputSnapshot",
    "ManualExportProvenance",
    "ParkFactor",
    "ParkInputs",
    "ParkVenue",
    "PitchTypeSplit",
    "RoofStatus",
    "SnapshotField",
    "SourceAvailability",
    "SourceKind",
    "SourceRecord",
    "SwingShare",
    "VenueType",
    "WeatherForecast",
    "Window",
    "WindowedBatterMetrics",
]
