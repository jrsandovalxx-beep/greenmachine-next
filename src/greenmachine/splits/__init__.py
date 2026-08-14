"""Pitch-type split policy for the §GMF-003 metrics screen.

Eligibility — which pitch types a screen shows — lives here rather than in the
input contract, because it is a display policy applied by the screen from data
in the snapshot (§7), not a property of the data.
"""

from greenmachine.splits.eligibility import (
    DEFAULT_USAGE_THRESHOLD,
    Eligibility,
    EligibilityVerdict,
    classify_usage,
)

__all__ = [
    "DEFAULT_USAGE_THRESHOLD",
    "Eligibility",
    "EligibilityVerdict",
    "classify_usage",
]
