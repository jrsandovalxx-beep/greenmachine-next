"""Eligibility is decided by usage alone — proved, not asserted.

§GMF-003 criterion 3 needs three states, and needs the third to stay distinct:
a pitch type whose usage was never observed is *unevaluable*, not *below
threshold*. It also needs eligibility and availability kept apart, so one
missing metric can never suppress a qualifying pitch type. The combinatorial
test below is what turns that from a design intention into a measured fact.

This module builds its own splits rather than importing the GMF-001 synthetic
builders, and that is not merely an import convenience: classifying eligibility
needs no snapshot, no source table and no window — only a usage field. A test
that had to assemble a snapshot to ask this question would be evidence the
separation had leaked. Its numbers follow the same OQ-4 discipline: obviously
non-baseball, so no fixture value can read as a judgment.
"""

from __future__ import annotations

import dataclasses
import itertools
from decimal import Decimal

import pytest

from greenmachine.inputs import (
    AbsenceReason,
    BattedBallRate,
    ExitVelocityAverage,
    ExpectedWeightedOnBase,
    IsolatedPower,
    PitchTypeSplit,
    SnapshotField,
    SwingingStrikeRate,
    UsageShare,
    WhiffRate,
)
from greenmachine.splits import (
    DEFAULT_USAGE_THRESHOLD,
    Eligibility,
    EligibilityVerdict,
    classify_usage,
)

SOURCE = "synthetic-eligibility-fixture"

# The six metrics that are not usage. Eligibility must be invariant over every
# combination of their presence and absence.
METRIC_FIELDS = (
    "barrel_rate",
    "exit_velocity",
    "isolated_power",
    "expected_woba",
    "whiff_rate",
    "swinging_strike_rate",
)


def _usage_field(share: str) -> SnapshotField[UsageShare]:
    return SnapshotField.present(UsageShare(share=Decimal(share), sample_pitches=100), SOURCE)


def _split(share: str) -> PitchTypeSplit:
    """A pitch type with every metric present, at a given usage share."""
    return PitchTypeSplit(
        pitch_type="ZZ",
        usage_share=_usage_field(share),
        barrel_rate=SnapshotField.present(
            BattedBallRate(rate=Decimal("0.999"), batted_ball_events=1), SOURCE
        ),
        exit_velocity=SnapshotField.present(
            ExitVelocityAverage(miles_per_hour=Decimal("1.5"), batted_ball_events=1), SOURCE
        ),
        isolated_power=SnapshotField.present(
            IsolatedPower(points=Decimal("2.998"), at_bats=1), SOURCE
        ),
        expected_woba=SnapshotField.present(
            ExpectedWeightedOnBase(value=Decimal("3.997"), plate_appearances=1), SOURCE
        ),
        whiff_rate=SnapshotField.present(WhiffRate(rate=Decimal("0.001"), swings=2), SOURCE),
        swinging_strike_rate=SnapshotField.present(
            SwingingStrikeRate(rate=Decimal("0.002"), pitches=3), SOURCE
        ),
    )


def test_the_threshold_is_fifteen_percent_as_a_share() -> None:
    """Stated as a share, matching UsageShare's unit, so the comparison never
    crosses a percent-versus-share boundary."""
    threshold = DEFAULT_USAGE_THRESHOLD
    assert threshold == Decimal("0.15")


@pytest.mark.parametrize("share", ["0.15", "0.16", "0.5", "1"])
def test_usage_at_or_above_the_threshold_qualifies(share: str) -> None:
    verdict = classify_usage(_usage_field(share))
    assert verdict.eligibility is Eligibility.QUALIFIES
    assert verdict.is_shown
    assert verdict.share == Decimal(share)
    assert verdict.absence is None


@pytest.mark.parametrize("share", ["0", "0.01", "0.149"])
def test_usage_below_the_threshold_is_suppressed_with_its_share_kept(share: str) -> None:
    """Suppressed, not dropped: the verdict keeps the share, so the screen can
    acknowledge the type by name and say what its usage actually was."""
    verdict = classify_usage(_usage_field(share))
    assert verdict.eligibility is Eligibility.BELOW_THRESHOLD
    assert not verdict.is_shown
    assert verdict.share == Decimal(share)
    assert verdict.absence is None


def test_a_true_zero_share_suppresses_as_a_measurement_not_an_absence() -> None:
    """Zero over a positive sample is a real observation — the pitch type was
    genuinely not thrown — and must not be laundered into an absence."""
    verdict = classify_usage(_usage_field("0"))
    assert verdict.eligibility is Eligibility.BELOW_THRESHOLD
    assert verdict.absence is None
    assert verdict.share == Decimal("0")


@pytest.mark.parametrize("reason", list(AbsenceReason))
def test_absent_usage_is_unevaluable_and_keeps_its_reason(reason: AbsenceReason) -> None:
    """Not "below threshold", which would assert something about a share nobody
    measured, and not a flattened "unknown", which would lose which kind of
    not-knowing this is."""
    source = None if reason is AbsenceReason.NOT_APPLICABLE else SOURCE
    usage: SnapshotField[UsageShare] = SnapshotField.absent(reason, source)
    verdict = classify_usage(usage)
    assert verdict.eligibility is Eligibility.UNEVALUABLE
    assert not verdict.is_shown
    assert verdict.share is None
    assert verdict.absence is reason


def test_every_eligibility_state_is_reachable() -> None:
    """Totality, measured: a three-state enum with an unreachable member would
    be a two-state decision wearing a third state's label."""
    reached = {
        classify_usage(_usage_field("0.5")).eligibility,
        classify_usage(_usage_field("0.01")).eligibility,
        classify_usage(SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE)).eligibility,
    }
    assert reached == set(Eligibility)


@pytest.mark.parametrize("share", ["0.5", "0.01"])
def test_eligibility_is_invariant_over_every_metric_availability_combination(share: str) -> None:
    """The separation criterion 3 requires, over all 2**6 combinations.

    A qualifying pitch type with an unavailable metric stays qualifying; a
    suppressed one stays suppressed. One missing metric never suppresses a type,
    because the classifier is not given the metrics to be influenced by.
    """
    baseline = classify_usage(_usage_field(share))
    absent: SnapshotField[object] = SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE)
    combinations = 0
    for present_flags in itertools.product([True, False], repeat=len(METRIC_FIELDS)):
        split = _split(share)
        overrides = {
            name: getattr(split, name) if keep else absent
            for name, keep in zip(METRIC_FIELDS, present_flags, strict=True)
        }
        candidate = dataclasses.replace(split, **overrides)
        assert classify_usage(candidate.usage_share) == baseline
        combinations += 1
    assert combinations == 2 ** len(METRIC_FIELDS) == 64


def test_the_classifier_cannot_see_the_other_metrics() -> None:
    """Stated structurally rather than behaviourally: the parameter is the usage
    field, not the split, so metric availability is not merely ignored — it is
    not in scope. Making the wrong thing unrepresentable beats forbidding it."""
    split = _split("0.5")
    with pytest.raises(AttributeError):
        classify_usage(split)  # type: ignore[arg-type]


def test_a_custom_threshold_is_applied_as_given() -> None:
    """The threshold is a parameter because the screen must state the number it
    applied; a constant buried in a branch could drift from the stated one."""
    usage = _usage_field("0.2")
    assert classify_usage(usage, Decimal("0.25")).eligibility is Eligibility.BELOW_THRESHOLD
    assert classify_usage(usage, Decimal("0.2")).eligibility is Eligibility.QUALIFIES


def test_the_verdict_sets_exactly_one_of_share_and_absence() -> None:
    """Mirrors SnapshotField's own exactly-one law, over all three states."""
    verdicts = [
        classify_usage(_usage_field("0.5")),
        classify_usage(_usage_field("0.01")),
        classify_usage(SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE)),
    ]
    for verdict in verdicts:
        assert isinstance(verdict, EligibilityVerdict)
        assert (verdict.share is None) != (verdict.absence is None)
