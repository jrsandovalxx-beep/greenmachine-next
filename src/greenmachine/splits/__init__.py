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
from greenmachine.splits.view import (
    ABSENCE_WORDS,
    DENOMINATORS,
    METRIC_COLUMNS,
    PITCH_TYPE_COLUMN,
    SplitScreen,
    SuppressedType,
    absence_notes,
    absent_metric_notes,
    build_screen,
    denominator_notes,
    provenance_notes,
    screen_frames,
    screen_rows,
    screen_state_frame,
    split_fields,
    suppression_notes,
    threshold_statement,
    window_label,
)

__all__ = [
    "ABSENCE_WORDS",
    "DEFAULT_USAGE_THRESHOLD",
    "DENOMINATORS",
    "METRIC_COLUMNS",
    "PITCH_TYPE_COLUMN",
    "Eligibility",
    "EligibilityVerdict",
    "SplitScreen",
    "SuppressedType",
    "absence_notes",
    "absent_metric_notes",
    "build_screen",
    "classify_usage",
    "denominator_notes",
    "provenance_notes",
    "screen_frames",
    "screen_rows",
    "screen_state_frame",
    "split_fields",
    "suppression_notes",
    "threshold_statement",
    "window_label",
]
