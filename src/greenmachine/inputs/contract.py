"""The GreenMachine input contract — the snapshot every screen renders.

Authored by GMF-001 (FEATURE_PHASE_PLAN §7, §GMF-001 criterion 2). The contract
is the product's spine: a screen renders an ``InputSnapshot`` and never fetches
(§7). Its principles, each carried by a construct below:

- **One snapshot, one moment.** ``InputSnapshot.captured_at`` is a tz-aware UTC
  timestamp supplied by the snapshot builder (never read from a clock here), and
  every contributing source is identified in ``InputSnapshot.sources``.
- **Windows are named.** ``Window`` carries D-025's hierarchy — ``RECENT_7D``,
  ``RECENT_14D``, ``SEASON_TO_DATE`` — so a screen requests a named window and
  does no date arithmetic.
- **Absence is a value.** Every observed field is a ``SnapshotField`` that
  distinguishes *not applicable*, *not yet observed* and *source unavailable*
  (``AbsenceReason``) from a present value. A field that collapses those into a
  bare ``None`` is the defect this module exists to prevent. Evidence
  confidence stays beside the value — the denominator count travels inside each
  value type (D-014) — and is never fused into it.
- **Denominators are named in the field.** Batted-ball rates use **BBE —
  Statcast batted-ball events, home runs included** — never the BABIP
  denominator, which excludes home runs and would silently remove the outcome
  this product exists to study. Each value type states its unit and denominator.
- **Pitch-type splits carry their usage share**, so GMF-003's 15% display
  threshold is applied by the screen from data in the snapshot.
- **Provenance travels with the data.** Every field names its contributing
  source by ``source_id``; a manual-export source carries the full
  ``ManualExportProvenance`` record, so D-057's manual-export chain is
  auditable from the snapshot alone.
- **Event detail is snapshot data, not a fetch.** A batter's plate-appearance
  log (``PlateAppearanceLog``) is carried in the snapshot at the same captured
  moment as the aggregates beside it, because a detail view is a view of the
  same instant: the log is reachable from more than one screen, so it is a
  shared property of the batter, and a popup renders it without fetching. Its
  population is every plate appearance; contact rates divide only by its
  ``batted_ball_events()`` subpopulation, the named denominator.

Structural identity fields (ids, names, enum members) are constructor
arguments validated at build time; the three-way absence semantics apply to
*observed* fields — every one of which is a ``SnapshotField``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, unique
from typing import Generic, TypeVar

from greenmachine.inputs.errors import InputContractError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

T = TypeVar("T")


@unique
class Window(Enum):
    """D-025's named windows. A screen states which window supplied a value."""

    RECENT_7D = "RECENT_7D"
    RECENT_14D = "RECENT_14D"
    SEASON_TO_DATE = "SEASON_TO_DATE"


@unique
class AbsenceReason(Enum):
    """The three distinguishable absence states (FEATURE_PHASE_PLAN §7)."""

    NOT_APPLICABLE = "not_applicable"
    NOT_YET_OBSERVED = "not_yet_observed"
    SOURCE_UNAVAILABLE = "source_unavailable"


@unique
class DisplayState(Enum):
    """The total rendering states of a field: a value, or a named absence."""

    VALUE = "value"
    NOT_APPLICABLE = "not_applicable"
    NOT_YET_OBSERVED = "not_yet_observed"
    SOURCE_UNAVAILABLE = "source_unavailable"


_ABSENCE_TO_DISPLAY = {
    AbsenceReason.NOT_APPLICABLE: DisplayState.NOT_APPLICABLE,
    AbsenceReason.NOT_YET_OBSERVED: DisplayState.NOT_YET_OBSERVED,
    AbsenceReason.SOURCE_UNAVAILABLE: DisplayState.SOURCE_UNAVAILABLE,
}


@dataclass(frozen=True)
class SnapshotField(Generic[T]):
    """An observed field: exactly one of ``value`` and ``absence`` is set.

    ``source_id`` names the contributing source in the snapshot's source table.
    It is required with a present value (provenance travels with the data) and
    optional with an absence (``SOURCE_UNAVAILABLE`` may still name the source
    that failed; ``NOT_APPLICABLE`` usually has none).
    """

    value: T | None
    absence: AbsenceReason | None
    source_id: str | None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.absence is None):
            raise InputContractError(
                "a SnapshotField carries exactly one of a value and an absence; "
                f"got value={self.value!r}, absence={self.absence!r}"
            )
        if self.value is not None and self.source_id is None:
            raise InputContractError("a present value must name its source_id")

    @classmethod
    def present(cls, value: T, source_id: str) -> SnapshotField[T]:
        return cls(value=value, absence=None, source_id=source_id)

    @classmethod
    def absent(cls, reason: AbsenceReason, source_id: str | None = None) -> SnapshotField[T]:
        return cls(value=None, absence=reason, source_id=source_id)

    def display_state(self) -> DisplayState:
        """Total over every constructible field; no default branch."""
        if self.value is not None:
            return DisplayState.VALUE
        if self.absence is None:  # unreachable past __post_init__, stated anyway
            raise InputContractError("field has neither value nor absence")
        return _ABSENCE_TO_DISPLAY[self.absence]


@dataclass(frozen=True)
class ManualExportProvenance:
    """D-053/D-057: the provenance record of a manual export, never a fetch."""

    source_url: str
    export_date: date
    row_count: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.source_url:
            raise InputContractError("provenance requires a source_url")
        if self.row_count <= 0:
            raise InputContractError("provenance row_count must be positive")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise InputContractError("provenance sha256 must be 64 lowercase hex digits")


@unique
class SourceKind(Enum):
    MANUAL_EXPORT = "manual_export"
    REFERENCE_DATA = "reference_data"
    LIVE_ADAPTER = "live_adapter"
    SYNTHETIC = "synthetic"


@unique
class SourceAvailability(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SourceRecord:
    """The identity of one contributing source at the snapshot's moment."""

    source_id: str
    kind: SourceKind
    description: str
    availability: SourceAvailability
    provenance: ManualExportProvenance | None = None

    def __post_init__(self) -> None:
        if not self.source_id:
            raise InputContractError("source_id must be non-empty")
        if self.kind is SourceKind.MANUAL_EXPORT and self.provenance is None:
            raise InputContractError(
                f"manual-export source {self.source_id!r} requires a provenance record (D-057)"
            )


def _require_share(name: str, share: Decimal) -> None:
    if not Decimal("0") <= share <= Decimal("1"):
        raise InputContractError(f"{name} must lie in [0, 1]; got {share}")


def _require_count(name: str, count: int) -> None:
    if count < 0:
        raise InputContractError(f"{name} must be non-negative; got {count}")


@dataclass(frozen=True)
class BattedBallRate:
    """Unit: share in [0, 1]. Denominator: **BBE — Statcast batted-ball events,
    home runs included** (never BABIP's HR-excluding denominator). The BBE count
    is the D-014 evidence axis and is displayed beside the rate, never fused."""

    rate: Decimal
    batted_ball_events: int

    def __post_init__(self) -> None:
        _require_share("rate", self.rate)
        _require_count("batted_ball_events", self.batted_ball_events)


@dataclass(frozen=True)
class ExitVelocityAverage:
    """Unit: miles per hour. Denominator: BBE (home runs included)."""

    miles_per_hour: Decimal
    batted_ball_events: int

    def __post_init__(self) -> None:
        if self.miles_per_hour <= 0:
            raise InputContractError("exit velocity must be positive")
        _require_count("batted_ball_events", self.batted_ball_events)


@dataclass(frozen=True)
class SwingShare:
    """Unit: share in [0, 1]. Denominator: tracked competitive swings (the
    D-023/D-026 ideal-attack-angle sample basis)."""

    share: Decimal
    tracked_swings: int

    def __post_init__(self) -> None:
        _require_share("share", self.share)
        _require_count("tracked_swings", self.tracked_swings)


@dataclass(frozen=True)
class AirBallShare:
    """Unit: share in [0, 1]. Denominator: air balls — fly balls plus line
    drives with valid coordinates (the D-023 Pull Air % basis)."""

    share: Decimal
    air_balls: int

    def __post_init__(self) -> None:
        _require_share("share", self.share)
        _require_count("air_balls", self.air_balls)


@dataclass(frozen=True)
class PitchTypeSplit:
    """A batter's contact quality against one pitch type.

    ``usage_share`` is the share of this pitch type within the sample the split
    was computed against, carried in the snapshot so GMF-003's 15% display
    threshold is applied by the screen, never assumed upstream (§7).
    """

    pitch_type: str
    usage_share: Decimal
    barrel_rate: SnapshotField[BattedBallRate]
    exit_velocity: SnapshotField[ExitVelocityAverage]

    def __post_init__(self) -> None:
        if not self.pitch_type:
            raise InputContractError("pitch_type must be non-empty")
        _require_share("usage_share", self.usage_share)


@dataclass(frozen=True)
class WindowedBatterMetrics:
    """The D-023 power surface for one named window."""

    window: Window
    barrel_rate: SnapshotField[BattedBallRate]
    exit_velocity: SnapshotField[ExitVelocityAverage]
    ideal_attack_angle_share: SnapshotField[SwingShare]
    pull_air_share: SnapshotField[AirBallShare]


@dataclass(frozen=True)
class ExitVelocityReading:
    """Unit: miles per hour — one event's measurement, not an aggregate."""

    miles_per_hour: Decimal

    def __post_init__(self) -> None:
        if self.miles_per_hour <= 0:
            raise InputContractError("exit velocity must be positive")


@dataclass(frozen=True)
class HitDistanceReading:
    """Unit: feet — one event's projected hit distance."""

    feet: Decimal

    def __post_init__(self) -> None:
        if self.feet < 0:
            raise InputContractError("hit distance cannot be negative")


@dataclass(frozen=True)
class PlateAppearanceEvent:
    """One plate appearance in a batter's log — display-only, never scored.

    The population is **every plate appearance** — strikeouts, walks,
    hit-by-pitches and sacrifices included (Product Owner ruling; the
    contact-for-power trade means strikeout frequency is half the profile).
    ``batted_ball`` is the BBE membership flag: it names whether this plate
    appearance ended with the ball in play, and it is the **denominator
    selector** for every contact rate (BBE stays the denominator for rates;
    the log is a different object with a different population).

    ``pitch_type`` and ``result`` carry the contributing source's own
    designations verbatim (provenance over invention: an enum authored here
    would contradict the real export's vocabulary at wire-through).
    ``batted_ball`` is assigned at the ingestion boundary by deriving
    membership from the pinned result vocabulary, **failing closed**: an
    unrecognized result errors at ingestion and never defaults in either
    direction — a default's sign silently biases every contact rate. GMF-006
    pins the observed vocabulary and proves this law at wire-through; the
    invariants below guard rows that disagree with themselves. Each
    measurement is a ``SnapshotField``; the trichotomy is load-bearing on
    ordinary rows: a non-contact plate appearance carries **NOT_APPLICABLE**
    for exit velocity and hit distance — nothing was hit, so the measurement
    is not applicable regardless of source health — while a batted ball with
    an untracked measurement carries ``SOURCE_UNAVAILABLE`` or
    ``NOT_YET_OBSERVED``, and never ``NOT_APPLICABLE``. Both directions are
    enforced.
    """

    event_date: date
    pitch_type: str
    result: str
    batted_ball: bool
    exit_velocity: SnapshotField[ExitVelocityReading]
    hit_distance: SnapshotField[HitDistanceReading]

    def __post_init__(self) -> None:
        if not self.pitch_type:
            raise InputContractError("event pitch_type must be non-empty")
        if not self.result:
            raise InputContractError("event result must be non-empty")
        measurements = (
            ("exit_velocity", self.exit_velocity),
            ("hit_distance", self.hit_distance),
        )
        if not self.batted_ball:
            for name, measurement in measurements:
                if measurement.absence is not AbsenceReason.NOT_APPLICABLE:
                    raise InputContractError(
                        f"a non-contact plate appearance carries NOT_APPLICABLE for {name}; "
                        f"got value={measurement.value!r}, absence={measurement.absence!r}"
                    )
        else:
            for name, measurement in measurements:
                if measurement.absence is AbsenceReason.NOT_APPLICABLE:
                    raise InputContractError(
                        f"a batted ball's {name} is applicable; an untracked measurement is "
                        "SOURCE_UNAVAILABLE or NOT_YET_OBSERVED, never NOT_APPLICABLE"
                    )


@dataclass(frozen=True)
class PlateAppearanceLog:
    """A batter's per-event plate-appearance log for one named window.

    A **present, empty** log is a real observation — the source is healthy and
    the batter had no plate appearances in the window — and renders as exactly
    that. It is distinct from the log being absent (``NOT_YET_OBSERVED``: not
    yet captured; ``SOURCE_UNAVAILABLE``: the source failed). Events are
    ordered by non-decreasing date so rendering is deterministic without
    screen-side sorting.

    Two populations live in this one structure, so the denominator is named
    in the API: a contact rate computed over ``events`` divides by plate
    appearances and comes out silently low by each batter's strikeout-and-walk
    share — the BABIP error in new clothes. ``batted_ball_events()`` is the
    BBE subpopulation, and every contact rate is computed over it.
    """

    window: Window
    events: tuple[PlateAppearanceEvent, ...]

    def __post_init__(self) -> None:
        dates = [event.event_date for event in self.events]
        if dates != sorted(dates):
            raise InputContractError("plate appearances must be ordered by non-decreasing date")

    def batted_ball_events(self) -> tuple[PlateAppearanceEvent, ...]:
        """The BBE subpopulation — the named denominator for contact rates."""
        return tuple(event for event in self.events if event.batted_ball)


@dataclass(frozen=True)
class BatterInputs:
    """One batter's observed inputs at the snapshot's moment.

    ``plate_appearance_log`` is a shared property of what a batter is in this
    product (it is reachable from more than one screen), captured at the same
    moment as every aggregate beside it — a detail view is a view of the same
    instant, so the log lives in the snapshot and a popup renders it without
    fetching (§7).
    """

    batter_id: str
    name: str
    windows: tuple[WindowedBatterMetrics, ...]
    pitch_type_splits: tuple[PitchTypeSplit, ...]
    plate_appearance_log: SnapshotField[PlateAppearanceLog]

    def __post_init__(self) -> None:
        if not self.batter_id:
            raise InputContractError("batter_id must be non-empty")
        if not self.name:
            raise InputContractError("batter name must be non-empty")
        seen = [metrics.window for metrics in self.windows]
        if len(seen) != len(set(seen)):
            raise InputContractError(f"batter {self.batter_id!r} repeats a window")
        split_types = [split.pitch_type for split in self.pitch_type_splits]
        if len(split_types) != len(set(split_types)):
            raise InputContractError(f"batter {self.batter_id!r} repeats a pitch type")

    def metrics_for(self, window: Window) -> WindowedBatterMetrics | None:
        for metrics in self.windows:
            if metrics.window is window:
                return metrics
        return None


@unique
class VenueType(Enum):
    """D-055: part of the park reference data."""

    OPEN_AIR = "open_air"
    FIXED_ROOF = "fixed_roof"
    RETRACTABLE_ROOF = "retractable_roof"


@unique
class RoofStatus(Enum):
    """Game-time roof state of a retractable venue (D-055)."""

    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


@unique
class Handedness(Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class ParkVenue:
    """Reference-data identity of one venue (GMF-001 criterion 3).

    ``venue_id`` is the reference slug and primary key. ``savant_venue_id``
    is the join column to the pinned Savant snapshot; its values come from
    the committed export (data/SAVANT_PARK_FACTORS_PROVENANCE.md), never
    from memory, and it is ``None`` exactly where the snapshot has no row
    for the club — a gap the product represents, never fills.
    """

    venue_id: str
    name: str
    team: str
    venue_type: VenueType
    savant_venue_id: int | None

    def __post_init__(self) -> None:
        if not self.venue_id or not self.name or not self.team:
            raise InputContractError("venue_id, name and team must be non-empty")


@dataclass(frozen=True)
class ParkFactor:
    """D-053: a Savant per-handedness park factor. Unit: index, 100 = neutral.

    ``plate_appearances`` is the sample behind the factor (``n_pa`` in the
    pinned snapshot) — the D-014 evidence axis carried as a field of the
    value, not decoration, so a screen cannot render a 13,560-PA factor
    identically to a 31,000-PA one without deciding to. The pinned snapshot
    is a three-season rolling window (2024-2026); a screen rendering these
    values states which window they describe.
    """

    factor: Decimal
    handedness: Handedness
    plate_appearances: int

    def __post_init__(self) -> None:
        if self.factor <= 0:
            raise InputContractError("park factor must be positive")
        if self.plate_appearances <= 0:
            raise InputContractError("park factor plate_appearances must be positive")


@dataclass(frozen=True)
class WeatherForecast:
    """The D-054 NWS forecast surface the GMF-004 seam binds. Units: °F, mph."""

    temperature_f: Decimal
    wind_speed_mph: Decimal
    wind_direction: str
    short_forecast: str

    def __post_init__(self) -> None:
        if self.wind_speed_mph < 0:
            raise InputContractError("wind speed cannot be negative")
        if not self.wind_direction or not self.short_forecast:
            raise InputContractError("wind_direction and short_forecast must be non-empty")


@dataclass(frozen=True)
class ParkInputs:
    """One venue's observed inputs: factors per handedness, roof, forecast.

    D-055's rendering rules live in the screens; the contract carries the
    states they need, enforced in both directions with venue type as the
    membership evidence: ``roof_status`` is absent with NOT_APPLICABLE - and
    no other reason - for open-air and fixed-roof venues, and for retractable
    venues is present (D-055's retractable-unknown is an explicit, PRESENT
    ``RoofStatus.UNKNOWN``, not an absence) or absent with SOURCE_UNAVAILABLE
    or NOT_YET_OBSERVED, never NOT_APPLICABLE. A forecast for a closed or
    fixed roof is suppressed by the screen with a stated reason, never
    silently.
    """

    venue: ParkVenue
    park_factor_lhb: SnapshotField[ParkFactor]
    park_factor_rhb: SnapshotField[ParkFactor]
    roof_status: SnapshotField[RoofStatus]
    forecast: SnapshotField[WeatherForecast]

    def __post_init__(self) -> None:
        for slot, wanted in (
            (self.park_factor_lhb, Handedness.LEFT),
            (self.park_factor_rhb, Handedness.RIGHT),
        ):
            if slot.value is not None and slot.value.handedness is not wanted:
                raise InputContractError(
                    f"venue {self.venue.venue_id!r}: park factor slot for {wanted.value} "
                    f"carries a {slot.value.handedness.value} factor"
                )
        if self.venue.venue_type is not VenueType.RETRACTABLE_ROOF:
            if self.roof_status.value is not None:
                raise InputContractError(
                    f"venue {self.venue.venue_id!r}: roof_status is observable only for "
                    "retractable roofs; open-air and fixed venues carry NOT_APPLICABLE"
                )
            if self.roof_status.absence is not AbsenceReason.NOT_APPLICABLE:
                raise InputContractError(
                    f"venue {self.venue.venue_id!r}: a roof that does not exist did not "
                    "fail and nothing is pending - the only absence is NOT_APPLICABLE"
                )
        elif self.roof_status.absence is AbsenceReason.NOT_APPLICABLE:
            raise InputContractError(
                f"venue {self.venue.venue_id!r}: a retractable roof's state is entirely "
                "applicable; an unknown state is a PRESENT RoofStatus.UNKNOWN (D-055), "
                "and an unobtained one is SOURCE_UNAVAILABLE or NOT_YET_OBSERVED"
            )


@dataclass(frozen=True)
class InputSnapshot:
    """One snapshot, one moment — the only thing a screen renders (§7)."""

    captured_at: datetime
    sources: tuple[SourceRecord, ...]
    batters: tuple[BatterInputs, ...]
    parks: tuple[ParkInputs, ...]

    def __post_init__(self) -> None:
        if (
            self.captured_at.tzinfo is None
            or self.captured_at.utcoffset() is None
            or self.captured_at.utcoffset() != timedelta(0)
        ):
            raise InputContractError(
                "captured_at must be timezone-aware UTC (utcoffset zero): one "
                "representation, normalised at the boundary — local ballpark time "
                "is a rendering concern, not a storage one"
            )
        if not self.sources:
            raise InputContractError("a snapshot names at least one source")
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise InputContractError("source ids must be unique")
        batter_ids = [batter.batter_id for batter in self.batters]
        if len(batter_ids) != len(set(batter_ids)):
            raise InputContractError("batter ids must be unique")
        venue_ids = [park.venue.venue_id for park in self.parks]
        if len(venue_ids) != len(set(venue_ids)):
            raise InputContractError("venue ids must be unique")
        known = set(source_ids)
        for owner, snapshot_field in self.iter_fields():
            if snapshot_field.source_id is not None and snapshot_field.source_id not in known:
                raise InputContractError(
                    f"{owner} names unknown source_id {snapshot_field.source_id!r}"
                )

    def source(self, source_id: str) -> SourceRecord:
        for record in self.sources:
            if record.source_id == source_id:
                return record
        raise InputContractError(f"unknown source_id {source_id!r}")

    def iter_fields(self) -> list[tuple[str, SnapshotField[object]]]:
        """Every observed field in the snapshot, with a describing owner label.

        The enumeration is structural (dataclass fields typed SnapshotField),
        so a field added to the contract is swept automatically rather than
        depending on someone remembering to extend a hand-kept list.
        """
        found: list[tuple[str, SnapshotField[object]]] = []

        def sweep(owner: str, node: object) -> None:
            for spec in fields(node):  # type: ignore[arg-type]
                candidate = getattr(node, spec.name)
                if isinstance(candidate, SnapshotField):
                    found.append((f"{owner}.{spec.name}", candidate))

        for batter in self.batters:
            sweep(f"batter {batter.batter_id}", batter)
            for metrics in batter.windows:
                sweep(f"batter {batter.batter_id} {metrics.window.value}", metrics)
            for split in batter.pitch_type_splits:
                sweep(f"batter {batter.batter_id} vs {split.pitch_type}", split)
            log = batter.plate_appearance_log.value
            if log is not None:
                for index, event in enumerate(log.events):
                    sweep(f"batter {batter.batter_id} event {index}", event)
        for park in self.parks:
            sweep(f"venue {park.venue.venue_id}", park)
        return found
