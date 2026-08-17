"""The contract's central claim, checked by CI rather than a reader's diligence.

``contract.py`` states: **every observed field is a ``SnapshotField``**;
structural identity fields (ids, names, enum members) are constructor
arguments. V2's finding 4 (``usage_share`` as a bare ``Decimal``) was that
prose rule escaping enforcement — a defect class that survived two review
passes. This module makes the rule mechanical: every dataclass field in the
contract is classified, and anything that is not a ``SnapshotField`` or a
child structure must appear in the explicit allow-list below with its
category stated. Adding a field that skips the contract now fails CI until
the addition is made visibly, in this list, under review.

The allow-list is deliberately flat and literal. A clever classifier that
inferred exemptions would be the same defect wearing a test's clothing —
and V3 proved it: this guard's first version exempted every Enum-typed field
wholesale, and `SourceRecord.availability` (dynamic state, not identity)
walked through exactly that hole. **An exemption is enumerated, never
inferred from a type.** Enum-typed fields now earn their entries one by one,
like everything else.

**One hole is left open deliberately, and is named here so it is not
rediscovered as a defect.** ``_contract_dataclasses`` excludes ``SnapshotField``
itself as the absence machinery, so a field added to *that* class is not swept
by this guard at all. ``SnapshotField.derivation`` (GMF-003) is such a field.
It is guarded instead by ``test_derivation.py`` and, more strongly, by
``InputSnapshot.__post_init__``, which rejects a derivation whose named inputs
do not resolve to fields of the same snapshot — an invariant rather than a
test. A future slot on ``SnapshotField`` gets no guard from this module and
must bring its own.
"""

from __future__ import annotations

import dataclasses
import types
import typing

from greenmachine.inputs import contract
from greenmachine.inputs.contract import SnapshotField

# (class, field) -> category. Every entry is a conscious exemption from the
# "every observed field is a SnapshotField" rule, and the category names why:
#   identity        - structural identity: ids, names, teams, enum taxonomy
#                     members that say WHICH thing this is (constructor args)
#   value-component - a component of one observed value, inside a SnapshotField
#                     payload (the D-014 evidence axis lives here)
#   vocabulary      - a contributing source's own designation, carried verbatim
#   membership      - the BBE membership flag, derived fail-closed at ingestion
#   provenance      - the D-053/D-057 manual-export provenance record
#   source-table    - the snapshot's source identity table
#   timestamp       - the snapshot's single captured moment
#   derivation      - the audit trail of a computed value: how it was computed
#                     and from which fields, carried so a derived value cannot
#                     be presented as a sourced one
ALLOWED_NON_SNAPSHOT_FIELDS: dict[tuple[str, str], str] = {
    ("ManualExportProvenance", "source_url"): "provenance",
    ("ManualExportProvenance", "export_date"): "provenance",
    ("ManualExportProvenance", "row_count"): "provenance",
    ("ManualExportProvenance", "sha256"): "provenance",
    ("SourceRecord", "source_id"): "source-table",
    ("SourceRecord", "kind"): "source-table",
    ("SourceRecord", "description"): "source-table",
    ("BattedBallRate", "rate"): "value-component",
    ("BattedBallRate", "batted_ball_events"): "value-component",
    ("ExitVelocityAverage", "miles_per_hour"): "value-component",
    ("ExitVelocityAverage", "batted_ball_events"): "value-component",
    ("SwingShare", "share"): "value-component",
    ("SwingShare", "tracked_swings"): "value-component",
    ("AirBallShare", "share"): "value-component",
    ("AirBallShare", "air_balls"): "value-component",
    ("UsageShare", "share"): "value-component",
    ("UsageShare", "sample_pitches"): "value-component",
    ("IsolatedPower", "points"): "value-component",
    ("IsolatedPower", "at_bats"): "value-component",
    ("ExpectedWeightedOnBase", "value"): "value-component",
    ("ExpectedWeightedOnBase", "plate_appearances"): "value-component",
    ("WhiffRate", "rate"): "value-component",
    ("WhiffRate", "swings"): "value-component",
    ("SwingingStrikeRate", "rate"): "value-component",
    ("SwingingStrikeRate", "pitches"): "value-component",
    ("ExitVelocityReading", "miles_per_hour"): "value-component",
    ("HitDistanceReading", "feet"): "value-component",
    ("PitchTypeSplit", "pitch_type"): "vocabulary",
    ("Derivation", "formula"): "derivation",
    ("Derivation", "inputs"): "derivation",
    ("WindowedBatterMetrics", "window"): "identity",
    ("WindowedPitchTypeSplits", "window"): "identity",
    ("PlateAppearanceLog", "window"): "identity",
    ("PlateAppearanceEvent", "event_date"): "identity",
    ("PlateAppearanceEvent", "pitch_type"): "vocabulary",
    ("PlateAppearanceEvent", "result"): "vocabulary",
    ("PlateAppearanceEvent", "batted_ball"): "membership",
    ("BatterInputs", "batter_id"): "identity",
    ("BatterInputs", "name"): "identity",
    ("ParkVenue", "venue_id"): "identity",
    ("ParkVenue", "name"): "identity",
    ("ParkVenue", "team"): "identity",
    ("ParkVenue", "venue_type"): "identity",
    ("ParkVenue", "savant_venue_id"): "identity",
    ("ParkFactor", "factor"): "value-component",
    ("ParkFactor", "handedness"): "value-component",
    ("ParkFactor", "plate_appearances"): "value-component",
    ("WeatherForecast", "temperature_f"): "value-component",
    ("WeatherForecast", "wind_speed_mph"): "value-component",
    ("WeatherForecast", "wind_direction"): "value-component",
    ("WeatherForecast", "short_forecast"): "value-component",
    ("InputSnapshot", "captured_at"): "timestamp",
}


def _contract_dataclasses() -> dict[str, type]:
    """Every dataclass defined in the contract module, except the mechanism
    class ``SnapshotField`` itself (its value/absence/source_id slots are the
    absence machinery, not contract structure)."""
    found = {
        name: obj
        for name, obj in vars(contract).items()
        if dataclasses.is_dataclass(obj)
        and isinstance(obj, type)
        and obj.__module__ == contract.__name__
        and obj is not SnapshotField
    }
    assert found, "the sweep found no dataclasses - the walk itself is broken"
    return found


def _is_snapshot_field(hint: object) -> bool:
    return hint is SnapshotField or typing.get_origin(hint) is SnapshotField


def _is_contract_structure(hint: object, classes: dict[str, type]) -> bool:
    """A child structure: a contract dataclass, an Optional of one, or a
    tuple of them - each is itself swept, so nothing hides inside."""
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        args = [arg for arg in typing.get_args(hint) if arg is not type(None)]
        return len(args) == 1 and _is_contract_structure(args[0], classes)
    if origin is tuple:
        args = [arg for arg in typing.get_args(hint) if arg is not Ellipsis]
        return bool(args) and all(_is_contract_structure(arg, classes) for arg in args)
    return isinstance(hint, type) and hint in classes.values()


def test_every_contract_field_is_a_snapshot_field_a_structure_or_allow_listed() -> None:
    classes = _contract_dataclasses()
    violations: list[str] = []
    for name, cls in sorted(classes.items()):
        hints = typing.get_type_hints(cls)
        for field in dataclasses.fields(cls):
            hint = hints[field.name]
            if _is_snapshot_field(hint):
                continue
            if _is_contract_structure(hint, classes):
                continue
            # No type is exempt wholesale - not even Enum. V3's finding: an
            # enum can carry dynamic state (SourceRecord.availability), so an
            # exemption is enumerated in the allow-list, never inferred here.
            if (name, field.name) not in ALLOWED_NON_SNAPSHOT_FIELDS:
                violations.append(
                    f"{name}.{field.name}: {hint!r} is not a SnapshotField, not a "
                    "contract structure, and not allow-listed - observed data is "
                    "leaving the contract by a side door"
                )
    assert not violations, "\n".join(violations)


def test_the_allow_list_carries_no_stale_entries() -> None:
    """Quiet growth control, both directions: an entry whose field no longer
    exists is rot, and an entry naming a SnapshotField-typed field would be
    the list exempting the very rule it serves."""
    classes = _contract_dataclasses()
    for (class_name, field_name), category in ALLOWED_NON_SNAPSHOT_FIELDS.items():
        assert category, f"({class_name}, {field_name}) has no stated category"
        assert class_name in classes, f"allow-list names unknown class {class_name!r}"
        cls = classes[class_name]
        field_names = {field.name for field in dataclasses.fields(cls)}
        assert field_name in field_names, (
            f"allow-list names unknown field {class_name}.{field_name!r}"
        )
        hint = typing.get_type_hints(cls)[field_name]
        assert not _is_snapshot_field(hint), (
            f"{class_name}.{field_name} is a SnapshotField and must not be allow-listed"
        )
