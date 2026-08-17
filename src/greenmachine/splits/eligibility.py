"""Which pitch types a screen shows — decided by usage alone.

§GMF-003 criterion 3 shows batter metrics against pitch types "only above 15%
usage share", with the threshold stated on the screen and suppressed types
visibly acknowledged rather than silently dropped. That is **three** states,
not two, and the third is the one a two-state reading loses:

- ``QUALIFIES`` — usage observed, at or above the threshold. The type is shown.
- ``BELOW_THRESHOLD`` — usage observed, under the threshold. The type is
  genuinely suppressed, and is acknowledged **by name** with the threshold
  stated. A bare count would be a silent drop wearing a number.
- ``UNEVALUABLE`` — usage was never observed, so the question was never
  reached. This is *not* "below threshold": that would assert something about a
  share nobody measured. The absence reason travels with the verdict, so the
  screen says which kind of not-knowing this is rather than flattening all
  three into "unknown".

**Eligibility and availability are separate questions, and the signature is
what keeps them separate.** ``classify_usage`` takes the usage field, not the
split, so it *cannot* read the other six metrics — a qualifying pitch type
whose xwOBA is unavailable stays displayed with that one cell absent. Making
the wrong thing unrepresentable is stronger than forbidding it in prose, and
this module is where that particular confusion would otherwise live.

The threshold is a parameter with a stated default rather than a constant
buried in a branch, because §7 requires the screen to apply it from data in the
snapshot and the screen must state the number it applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, unique

from greenmachine.inputs import AbsenceReason, SnapshotField, UsageShare

# §GMF-003 criterion 3's threshold. A share in [0, 1], matching UsageShare's
# unit, so the comparison never crosses a percent-versus-share boundary.
DEFAULT_USAGE_THRESHOLD = Decimal("0.15")


@unique
class Eligibility(Enum):
    """Total over the three states. There is no default branch and no fourth
    state: a present share is either at/above the threshold or below it, and an
    absent share is unevaluable."""

    QUALIFIES = "qualifies"
    BELOW_THRESHOLD = "below_threshold"
    UNEVALUABLE = "unevaluable"


@dataclass(frozen=True)
class EligibilityVerdict:
    """An eligibility decision with the evidence that produced it.

    ``share`` is the observed usage where one was observed, so a screen can
    state *why* a type was suppressed rather than only that it was.
    ``absence`` is the reason the usage was missing where it was missing, so an
    unevaluable type keeps its specific not-knowing. Exactly one of the two is
    set, which mirrors ``SnapshotField``'s own law.
    """

    eligibility: Eligibility
    share: Decimal | None
    absence: AbsenceReason | None

    @property
    def is_shown(self) -> bool:
        """Only a qualifying type is displayed as a metric row. The other two
        are acknowledged, by name, in their own stated groups — never dropped."""
        return self.eligibility is Eligibility.QUALIFIES


def classify_usage(
    usage: SnapshotField[UsageShare],
    threshold: Decimal = DEFAULT_USAGE_THRESHOLD,
) -> EligibilityVerdict:
    """Classify one pitch type's eligibility from its usage share alone.

    Note what this function cannot see: it receives the usage field, not the
    split, so no metric's availability can influence the verdict. That is the
    separation criterion 3 requires, enforced by the type rather than by care.

    A **present zero over a positive sample** is a real measurement — the pitch
    type was genuinely not thrown — so it classifies as ``BELOW_THRESHOLD`` and
    is acknowledged by name. It never becomes an absence, which would claim the
    share was unknown when it was in fact observed to be zero.
    """
    observed = usage.value
    if observed is None:
        # Unevaluable, with the reason kept. The contract guarantees a field
        # without a value carries an absence, so this is total, not a fallback.
        assert usage.absence is not None  # the contract's exactly-one law
        return EligibilityVerdict(
            eligibility=Eligibility.UNEVALUABLE, share=None, absence=usage.absence
        )
    if observed.share >= threshold:
        return EligibilityVerdict(
            eligibility=Eligibility.QUALIFIES, share=observed.share, absence=None
        )
    return EligibilityVerdict(
        eligibility=Eligibility.BELOW_THRESHOLD, share=observed.share, absence=None
    )
