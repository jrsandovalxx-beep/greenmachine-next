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
- **Denominators are named in the field, and positive.** Batted-ball rates use
  **BBE — Statcast batted-ball events, home runs included** — never the BABIP
  denominator, which excludes home runs and would silently remove the outcome
  this product exists to study. Each value type states its unit and denominator,
  and an aggregate's denominator is **positive by construction**: a rate over
  zero events is not a value, so a zero-sample aggregate travels as a named
  absence. The observed zero is not lost — it is carried by the absence reason
  (``NOT_YET_OBSERVED`` from a healthy source means the window has accumulated
  no events; ``SOURCE_UNAVAILABLE`` means the count is unknown), a vocabulary
  the snapshot builder applies at ingestion and GMF-006 proves at wire-through.
- **Pitch-type splits carry their usage share as an observed field** —
  ``SnapshotField[UsageShare]``, the share beside the sample it was computed
  against — so GMF-003's 15% display threshold is applied by the screen from
  data in the snapshot, and an unavailable usage is a named absence, distinct
  from a true zero share (which is a present value over a positive sample).
- **Pitch-type splits are bound to the window that produced them.**
  ``WindowedPitchTypeSplits`` carries the window once, for the whole set, at
  the level at which it is true — a window describes a computation, not an
  individual pitch type — so a screen naming its window reads that name off the
  structure that produced its rows. Each split's seven metrics carry their own
  denominators, which are **not** all the same population: barrel rate and exit
  velocity divide by BBE, ISO by at-bats, xwOBA by plate appearances, whiff rate
  by swings, swinging-strike rate by pitches of that type, and usage by every
  tracked pitch of every type. Several of those counts are arithmetically
  related, and none substitutes for another.
- **Sourced and derived values stay distinguishable.** A value the source
  supplied carries no ``Derivation``; a value this product computed carries one,
  naming its formula and the fields it consumed, and the snapshot checks those
  inputs resolve. ``SnapshotField.present`` cannot make the derived claim and
  ``SnapshotField.derived`` cannot avoid it, so a computed rate cannot reach a
  screen dressed as a sourced one.
- **Provenance travels with the data — with absences as much as with values.**
  Every present field names its contributing source by ``source_id``, and so
  does every **source-dependent absence**: ``SOURCE_UNAVAILABLE`` and
  ``NOT_YET_OBSERVED`` must name the source they implicate (only
  ``NOT_APPLICABLE`` may omit it). A manual-export source carries the full
  ``ManualExportProvenance`` record, so D-057's manual-export chain is
  auditable from the snapshot alone.
- **Source health has one representation.** The source table carries identity
  and provenance only — there is no availability flag, because a source's
  health at the captured moment is not one fact (an adapter can answer one
  query and fail another inside the same capture). Health lives per
  observation in the absence reasons, which are self-describing:
  ``SOURCE_UNAVAILABLE`` = consulted, did not answer; ``NOT_YET_OBSERVED`` =
  answered, nothing accumulated. Nothing exists for the fields to contradict.
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
class Derivation:
    """How a derived value was computed — the audit trail that keeps a derived
    value from being presented as a sourced one.

    A rate computed from other fields and displayed beside sourced rates is
    indistinguishable from them unless the data says otherwise, and this metric
    surface is dense with arithmetic identities that make such a computation
    easy and quiet: ``SwStr% = Whiff% * Swing%`` determines any one of the three
    from the other two, and ``UsageShare``'s two components multiply out to the
    pitch count that is ``SwingingStrikeRate``'s denominator. Wherever two
    columns' denominators are arithmetically related, one column can be
    manufactured from another; carrying the derivation is what makes that
    visible instead of invisible.

    ``inputs`` names the fields consumed, by their ``InputSnapshot.iter_fields``
    labels, and the snapshot checks that every one resolves to a field that
    actually exists — so "auditable" is a property the contract enforces rather
    than a claim a string makes.
    """

    formula: str
    inputs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.formula.strip():
            raise InputContractError("a derivation must state the formula it applied")
        if not self.inputs:
            raise InputContractError(
                "a derivation must name at least one input field: a value derived "
                "from nothing is either a sourced value or an invention"
            )
        if any(not label.strip() for label in self.inputs):
            raise InputContractError("a derivation's input labels must each be non-empty")


@dataclass(frozen=True)
class SnapshotField(Generic[T]):
    """An observed field: exactly one of ``value`` and ``absence`` is set.

    ``source_id`` names the contributing source in the snapshot's source table.
    It is required with a present value, and required with a
    **source-dependent absence**: ``SOURCE_UNAVAILABLE`` (the source was
    consulted and did not answer) and ``NOT_YET_OBSERVED`` (the source answered
    and the quantity has not accumulated) each implicate a source, and §7's
    "provenance travels with the data" keeps that implication auditable. Only
    ``NOT_APPLICABLE`` may omit it — a strikeout's exit velocity implicates no
    source and correctly names none.

    ``derivation`` separates a **sourced** value from a **derived** one. It is
    ``None`` for every value the source supplied directly — which is what
    ``present()`` constructs, so no existing field changes meaning — and
    ``derived()`` is the only way to make the other claim. A derived field may
    also be absent: a derivation propagates its inputs' absence with the reason
    intact, and the derivation record survives to say which input was missing.
    """

    value: T | None
    absence: AbsenceReason | None
    source_id: str | None
    derivation: Derivation | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.absence is None):
            raise InputContractError(
                "a SnapshotField carries exactly one of a value and an absence; "
                f"got value={self.value!r}, absence={self.absence!r}"
            )
        if self.value is not None and self.source_id is None:
            raise InputContractError("a present value must name its source_id")
        if (
            self.absence in (AbsenceReason.SOURCE_UNAVAILABLE, AbsenceReason.NOT_YET_OBSERVED)
            and self.source_id is None
        ):
            raise InputContractError(
                f"a {self.absence.value} absence implicates a source and must name it; "
                "only NOT_APPLICABLE may omit source_id"
            )

    @classmethod
    def present(cls, value: T, source_id: str) -> SnapshotField[T]:
        """A value the source supplied directly. Never a derived value."""
        return cls(value=value, absence=None, source_id=source_id)

    @classmethod
    def absent(
        cls,
        reason: AbsenceReason,
        source_id: str | None = None,
        derivation: Derivation | None = None,
    ) -> SnapshotField[T]:
        return cls(value=None, absence=reason, source_id=source_id, derivation=derivation)

    @classmethod
    def derived(
        cls, value: T, formula: str, inputs: tuple[str, ...], source_id: str
    ) -> SnapshotField[T]:
        """A value this product computed. The only constructor that makes the
        derived claim, so a derived value cannot reach a screen wearing a
        sourced value's clothes."""
        return cls(
            value=value,
            absence=None,
            source_id=source_id,
            derivation=Derivation(formula=formula, inputs=inputs),
        )

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


@dataclass(frozen=True)
class SourceRecord:
    """The identity and provenance of one contributing source — and nothing else.

    Health is deliberately not here. A source's health at the captured moment
    is not one fact — a live adapter can answer one query and fail another
    inside the same capture — so it lives **per observation**, in each field's
    absence reason: ``SOURCE_UNAVAILABLE`` means this source was consulted for
    that field and did not answer; ``NOT_YET_OBSERVED`` means it answered and
    the quantity has not accumulated. One fact, one representation: a
    table-level availability flag would be a second representation of the
    fields' own story, needing a consistency law to patrol the seam — and a
    row that can disagree with itself is the defect class this contract
    exists to prevent.
    """

    source_id: str
    kind: SourceKind
    description: str
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


def _require_positive_count(name: str, count: int) -> None:
    if count <= 0:
        raise InputContractError(
            f"{name} must be positive; got {count} — an aggregate over zero events "
            "is not a value, so a zero-sample aggregate travels as a named absence"
        )


@dataclass(frozen=True)
class BattedBallRate:
    """Unit: share in [0, 1]. Denominator: **BBE — Statcast batted-ball events,
    home runs included** (never BABIP's HR-excluding denominator). The BBE count
    is the D-014 evidence axis and is displayed beside the rate, never fused.
    It is positive by construction: a rate over zero batted balls is undefined
    and travels as a named absence, never as a constructed zero."""

    rate: Decimal
    batted_ball_events: int

    def __post_init__(self) -> None:
        _require_share("rate", self.rate)
        _require_positive_count("batted_ball_events", self.batted_ball_events)


@dataclass(frozen=True)
class ExitVelocityAverage:
    """Unit: miles per hour. Denominator: BBE (home runs included), positive
    by construction — an average over zero events is a named absence."""

    miles_per_hour: Decimal
    batted_ball_events: int

    def __post_init__(self) -> None:
        if self.miles_per_hour <= 0:
            raise InputContractError("exit velocity must be positive")
        _require_positive_count("batted_ball_events", self.batted_ball_events)


@dataclass(frozen=True)
class SwingShare:
    """Unit: share in [0, 1]. Denominator: tracked competitive swings (the
    D-023/D-026 ideal-attack-angle sample basis), positive by construction."""

    share: Decimal
    tracked_swings: int

    def __post_init__(self) -> None:
        _require_share("share", self.share)
        _require_positive_count("tracked_swings", self.tracked_swings)


@dataclass(frozen=True)
class AirBallShare:
    """Unit: share in [0, 1]. Denominator: air balls — fly balls plus line
    drives with valid coordinates (the D-023 Pull Air % basis), positive by
    construction."""

    share: Decimal
    air_balls: int

    def __post_init__(self) -> None:
        _require_share("share", self.share)
        _require_positive_count("air_balls", self.air_balls)


@dataclass(frozen=True)
class UsageShare:
    """Unit: share in [0, 1]. Denominator: **every tracked pitch of every type**
    in the sample the split was computed against — that whole-sample
    denominator is what makes usage a share of the batter's pitch mix.
    Positive by construction.

    ``sample_pitches`` is **not** the count of pitches of this one type, which
    is what ``SwingingStrikeRate`` divides by. The two sit in adjacent columns,
    both are "pitches", and they are different populations: this one counts
    across every type, that one counts within one. Their product with ``share``
    is precisely the other's denominator, so they are related by arithmetic and
    still not interchangeable.

    A **zero share over a positive sample is a present value** — the pitch
    type was genuinely not thrown — distinct from the usage being absent
    (``SOURCE_UNAVAILABLE``/``NOT_YET_OBSERVED``), which omission of a bare
    number could never express.
    """

    share: Decimal
    sample_pitches: int

    def __post_init__(self) -> None:
        _require_share("share", self.share)
        _require_positive_count("sample_pitches", self.sample_pitches)


@dataclass(frozen=True)
class IsolatedPower:
    """Unit: isolated power (slugging minus batting average), in points of
    extra-base power per at-bat. Denominator: **at-bats** — never plate
    appearances, which include walks and hit-by-pitch and would deflate the
    figure by each batter's walk share, the BABIP error transposed.

    **Not a share.** ISO's ceiling is 3.000 — every at-bat a home run gives
    slugging 4.000 against a 1.000 average — so ``_require_share``'s [0, 1]
    bound is wrong here and is deliberately not used. The bound below is exact,
    not a plausibility judgement.
    """

    points: Decimal
    at_bats: int

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.points <= Decimal("3"):
            raise InputContractError(
                f"isolated power must lie in [0, 3]; got {self.points} — the ceiling "
                "is 3.000 (every at-bat a home run), and ISO is not a [0, 1] share"
            )
        _require_positive_count("at_bats", self.at_bats)


@dataclass(frozen=True)
class ExpectedWeightedOnBase:
    """Unit: xwOBA, on the wOBA scale. Denominator: **plate appearances**
    ending on this pitch type.

    This is xwOBA in the standard meaning of the name, and specifically **not
    xwOBACON**, which divides by batted-ball events. The two share a name-stem,
    are both published per pitch type, and are different numbers over different
    populations — one counts every plate appearance the pitch type ended,
    the other only those that produced contact.

    **Not a share.** The wOBA scale is a weighted average whose largest event
    weight exceeds 1, so [0, 1] is the wrong bound. The bound below is a scale
    guard whose purpose is to catch a units mix-up — 400 or 40.0 where 0.400
    was meant — not to police baseball plausibility.
    """

    value: Decimal
    plate_appearances: int

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.value <= Decimal("4"):
            raise InputContractError(
                f"xwOBA must lie on the wOBA scale in [0, 4]; got {self.value} — this "
                "bound catches a units mix-up, and xwOBA is not a [0, 1] share"
            )
        _require_positive_count("plate_appearances", self.plate_appearances)


@dataclass(frozen=True)
class WhiffRate:
    """Unit: share in [0, 1]. Denominator: **swings** at this pitch type.

    ``WhiffRate`` and ``SwingingStrikeRate`` carry the *same numerator* —
    swinging strikes — over different denominators, so ``SwStr% = Whiff% *
    Swing%`` and any two of the three determine the third. That identity makes
    either rate computable from the other, which is exactly why neither may be
    computed and presented as sourced: a derived value says so through
    ``SnapshotField.derived``, or it does not appear.

    The denominator is not recoverable from the other rate's field, which is
    the correct behaviour rather than a gap: a rate over a denominator that was
    never observed cannot be derived at all.
    """

    rate: Decimal
    swings: int

    def __post_init__(self) -> None:
        _require_share("rate", self.rate)
        _require_positive_count("swings", self.swings)


@dataclass(frozen=True)
class SwingingStrikeRate:
    """Unit: share in [0, 1]. Denominator: **pitches of this pitch type** —
    not swings, which is ``WhiffRate``'s denominator, and not the whole-sample
    pitch count in ``UsageShare.sample_pitches``, which spans every type.

    Three counts within reach of this one screen are all called "pitches" or
    "swings" and none may stand in for another. See ``WhiffRate`` for the
    identity that links the two rates, and ``UsageShare`` for the product that
    reconstructs this denominator from usage's two components.
    """

    rate: Decimal
    pitches: int

    def __post_init__(self) -> None:
        _require_share("rate", self.rate)
        _require_positive_count("pitches", self.pitches)


@dataclass(frozen=True)
class PitchTypeSplit:
    """A batter's measured performance against one pitch type: seven metrics,
    each over its own named denominator.

    ``usage_share`` is observed data — a measured share with the sample it was
    computed against — so it is a ``SnapshotField`` like every observed field
    here, never a bare number: GMF-003's 15% display threshold is applied by
    the screen from data in the snapshot (§7), and the screen can distinguish
    an unavailable usage (named absence) from a true zero share (present
    ``UsageShare`` over a positive sample).

    **Eligibility and availability are separate questions**, and the structure
    keeps them separate. Whether this pitch type is shown at all is decided by
    ``usage_share`` alone; whether any one metric has a number is each field's
    own business. A qualifying pitch type with an unavailable xwOBA is a
    displayed row with one absent cell — one missing metric never suppresses
    the type, and an unevaluable usage is not a metric-level question at all.

    **No field defaults.** Every metric is supplied explicitly at construction,
    so a metric that was never considered cannot arrive looking like a metric
    that was considered and found absent.
    """

    pitch_type: str
    usage_share: SnapshotField[UsageShare]
    barrel_rate: SnapshotField[BattedBallRate]
    exit_velocity: SnapshotField[ExitVelocityAverage]
    isolated_power: SnapshotField[IsolatedPower]
    expected_woba: SnapshotField[ExpectedWeightedOnBase]
    whiff_rate: SnapshotField[WhiffRate]
    swinging_strike_rate: SnapshotField[SwingingStrikeRate]

    def __post_init__(self) -> None:
        if not self.pitch_type:
            raise InputContractError("pitch_type must be non-empty")


@dataclass(frozen=True)
class WindowedPitchTypeSplits:
    """The pitch-type split set one named window produced.

    **The window binds here, not on each split.** A window is a property of the
    computation that produced the whole set, not of an individual pitch type,
    and a per-split window field would let one batter's splits disagree with
    each other — a row that can disagree with itself, needing a consistency law
    to patrol the seam. This mirrors ``WindowedBatterMetrics``, which is the
    contract's already-established answer to the same question.

    A screen therefore reads the window it is displaying off ``window``, from
    the same structure that produced its rows, rather than from a separate
    constant that can drift out of agreement with them.

    ``splits`` is itself a ``SnapshotField`` because the set has its own absence
    story, one level above any metric's: a **present, empty** set is a real
    observation — the source answered and this batter faced no tracked pitches
    in the window — and is distinct from the set being absent
    (``NOT_YET_OBSERVED``: the window was never captured; ``SOURCE_UNAVAILABLE``:
    the source failed). Without the wrapper an empty tuple would have to carry
    both stories, which is the blank cell that could mean either.
    """

    window: Window
    splits: SnapshotField[tuple[PitchTypeSplit, ...]]

    def __post_init__(self) -> None:
        present = self.splits.value
        if present is None:
            return
        pitch_types = [split.pitch_type for split in present]
        if len(pitch_types) != len(set(pitch_types)):
            raise InputContractError(
                f"{self.window.value} splits repeat a pitch type: a pitch type is "
                "one row in one window, and a repeat is two answers to one question"
            )


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

    ``windows`` is **total over the named windows**: every batter carries all
    three ``Window`` members exactly once, and an unavailable window travels
    as a window whose fields are named absences — never as a missing entry.
    A tuple that could omit a window would force ``metrics_for`` to answer
    with a bare ``None`` (the collapsed absence this module exists to prevent)
    or to invent a reason for the omission — and an invented reason is a
    default, the thing the fail-closed ingestion law forbids.

    ``pitch_type_splits`` is total over the named windows for exactly the same
    reason, and ``splits_for`` is total for exactly the same reason. Each entry
    binds its window to the split set that window produced, so a screen naming
    a window names it from the structure that produced its rows.
    """

    batter_id: str
    name: str
    windows: tuple[WindowedBatterMetrics, ...]
    pitch_type_splits: tuple[WindowedPitchTypeSplits, ...]
    plate_appearance_log: SnapshotField[PlateAppearanceLog]

    def __post_init__(self) -> None:
        if not self.batter_id:
            raise InputContractError("batter_id must be non-empty")
        if not self.name:
            raise InputContractError("batter name must be non-empty")
        seen = [metrics.window for metrics in self.windows]
        if len(seen) != len(set(seen)):
            raise InputContractError(f"batter {self.batter_id!r} repeats a window")
        omitted = [window.value for window in Window if window not in set(seen)]
        if omitted:
            raise InputContractError(
                f"batter {self.batter_id!r} omits named window(s) {omitted}: the "
                "contract is total over windows — an unavailable window travels as "
                "absent fields, never as a missing entry"
            )
        split_windows = [windowed.window for windowed in self.pitch_type_splits]
        if len(split_windows) != len(set(split_windows)):
            raise InputContractError(f"batter {self.batter_id!r} repeats a split window")
        split_omitted = [window.value for window in Window if window not in set(split_windows)]
        if split_omitted:
            raise InputContractError(
                f"batter {self.batter_id!r} omits pitch-type splits for named "
                f"window(s) {split_omitted}: splits are total over windows for the "
                "same reason the metrics are — an uncaptured window travels as an "
                "absent split set naming its reason, never as a missing entry"
            )

    def metrics_for(self, window: Window) -> WindowedBatterMetrics:
        """Total: every named window resolves — absence lives in the fields."""
        for metrics in self.windows:
            if metrics.window is window:
                return metrics
        raise InputContractError(  # unreachable past __post_init__, stated anyway
            f"batter {self.batter_id!r} has no {window.value} entry"
        )

    def splits_for(self, window: Window) -> WindowedPitchTypeSplits:
        """Total: every named window resolves — absence lives in the split set.

        Totality is what lets this return a structure rather than ``None``. A
        bare ``None`` would be the collapsed absence this module exists to
        prevent: the caller could not tell an uncaptured window from a batter
        who faced nothing, and would have to invent a reason for the gap.
        """
        for windowed in self.pitch_type_splits:
            if windowed.window is window:
                return windowed
        raise InputContractError(  # unreachable past __post_init__, stated anyway
            f"batter {self.batter_id!r} has no {window.value} split entry"
        )


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

    ``latitude``/``longitude`` are **required** (§GMF-005). The NWS API is
    addressed only by coordinate — ``/points/{lat},{lon}`` — and publishes no
    venue-name endpoint, so a venue without coordinates cannot be asked about
    the weather at all. Making them required rather than optional means the
    type system cannot express an unaddressable venue, which is the same
    signature-enforcement §GMF-003 used for observed usage share. They are
    geographic facts about a fixed place, not provider data: D-052 and D-057
    do not reach them. Precision is stated where the values live
    (``park_reference``), not here.
    """

    venue_id: str
    name: str
    team: str
    venue_type: VenueType
    savant_venue_id: int | None
    latitude: Decimal
    longitude: Decimal

    def __post_init__(self) -> None:
        if not self.venue_id or not self.name or not self.team:
            raise InputContractError("venue_id, name and team must be non-empty")
        if not Decimal("-90") <= self.latitude <= Decimal("90"):
            raise InputContractError(
                f"venue {self.venue_id!r}: latitude {self.latitude} is outside [-90, 90]"
            )
        if not Decimal("-180") <= self.longitude <= Decimal("180"):
            raise InputContractError(
                f"venue {self.venue_id!r}: longitude {self.longitude} is outside [-180, 180]"
            )


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
    """The D-054 NWS forecast surface the GMF-004 seam binds. Units: °F, mph.

    ``obtained_at`` is **when this forecast was retrieved from its source** —
    not when the snapshot was assembled (§GMF-005). The two diverge the moment
    a cache exists: a cached forecast is older than the ``InputSnapshot`` that
    renders it, and that gap is exactly what a stated freshness bound has to
    make visible to a reader.

    It lives on the value rather than on ``SourceRecord`` for that record's own
    stated reason: retrieval time at the captured moment **is not one fact**. A
    live adapter answers one venue from a fresh call and another from a cache
    filled twenty minutes earlier, so a table-level acquisition time would be a
    second representation of the values' own story — the defect class
    ``SourceRecord`` exists to prevent. ``ManualExportProvenance`` carries a
    single export date correctly because that export *is* one acquisition act
    for all of its rows; a live adapter has one per venue. The value travels
    through the cache, so its timestamp travels with it.
    """

    temperature_f: Decimal
    wind_speed_mph: Decimal
    wind_direction: str
    short_forecast: str
    obtained_at: datetime

    def __post_init__(self) -> None:
        if self.wind_speed_mph < 0:
            raise InputContractError("wind speed cannot be negative")
        if not self.wind_direction or not self.short_forecast:
            raise InputContractError("wind_direction and short_forecast must be non-empty")
        if (
            self.obtained_at.tzinfo is None
            or self.obtained_at.utcoffset() is None
            or self.obtained_at.utcoffset() != timedelta(0)
        ):
            raise InputContractError(
                "obtained_at must be timezone-aware UTC (utcoffset zero), the same "
                "single representation InputSnapshot.captured_at uses"
            )


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
        swept = self.iter_fields()
        known_labels = {owner for owner, _ in swept}
        for owner, snapshot_field in swept:
            if snapshot_field.source_id is not None and snapshot_field.source_id not in known:
                raise InputContractError(
                    f"{owner} names unknown source_id {snapshot_field.source_id!r}"
                )
            derivation = snapshot_field.derivation
            if derivation is None:
                continue
            # "Auditable" is enforced, not asserted: a derivation's named inputs
            # must resolve to fields that exist in this same snapshot, so the
            # audit trail cannot be a plausible-looking string.
            unresolved = [label for label in derivation.inputs if label not in known_labels]
            if unresolved:
                raise InputContractError(
                    f"{owner} derives from input(s) {unresolved} that name no field in "
                    "this snapshot; a derivation's inputs are iter_fields labels and "
                    "must resolve, or the audit trail is unverifiable"
                )
            if owner in derivation.inputs:
                raise InputContractError(f"{owner} names itself among its derivation inputs")

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
            for windowed in batter.pitch_type_splits:
                # The window enters the label because a pitch type now appears
                # once per window: without it the three would collide and a
                # label would no longer identify one field.
                #
                # CHANGING THIS FORMAT HAS A COST BEYOND READABILITY. These
                # labels are what `Derivation.inputs` names, and what
                # `__post_init__` resolves them against, so a format change
                # invalidates every derivation recorded in the old format. That
                # is not hypothetical: this very line's format changed in the
                # same revision that introduced the coupling, and had a
                # derivation existed then, it would have broken. Deliberately
                # not pinned by a test — the format must stay free to change —
                # so the obligation is to migrate recorded derivations with it.
                stem = f"batter {batter.batter_id} {windowed.window.value}"
                sweep(f"{stem} splits", windowed)
                splits = windowed.splits.value
                if splits is not None:
                    for split in splits:
                        sweep(f"{stem} vs {split.pitch_type}", split)
            log = batter.plate_appearance_log.value
            if log is not None:
                for index, event in enumerate(log.events):
                    sweep(f"batter {batter.batter_id} event {index}", event)
        for park in self.parks:
            sweep(f"venue {park.venue.venue_id}", park)
        return found
