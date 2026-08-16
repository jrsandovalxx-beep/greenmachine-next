"""The §GMF-003 metrics screen: pitch types down, seven metrics across.

Built on the §GMF-002 grid, not beside it. Every frame this module produces
comes from `greenmachine.grid.view`'s row-agnostic builders — the same numeric
frame, the same display texts riding the ``Styler``, the same hand-rolled green
scale and per-absence CSS (D-059/D-060). What this module adds is the row
source (pitch types instead of batters), the column set, and the screen policy
criterion 3 requires. There is one copy of the grading mechanism in the
repository and this is not it.

**Every metric names its own denominator**, because on this surface several of
them are near-neighbours that would otherwise read as interchangeable:

- Usage % divides by every tracked pitch of every type — never a filtered total.
- Barrel rate and exit velocity divide by BBE (home runs included, never BABIP).
- ISO divides by at-bats; xwOBA by plate appearances ending on the pitch type.
- Whiff% divides by **swings**; SwStr% by **pitches of that type**. Same
  numerator, different denominators — the pair that makes one rate quietly
  computable from the other.

**Nothing here derives anything.** Each metric states whether it came from the
source or was computed, read off ``SnapshotField.derivation`` rather than
asserted, so the claim on screen is a fact about the data rather than a caption.

**No ranking.** Pitch types render in neutral identity order — the type's own
name, ascending — exactly as the batter grid orders by name. The 15% threshold
is not a ranking: it is criterion 3's stated display rule, it is printed on the
screen, and every type it removes is named rather than dropped (D-015/D-017).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from greenmachine.grid import (
    FieldRow,
    MetricField,
    cell_text,
    display_state_frame,
    metric_fields,
    numeric_frame,
    style_frame_for,
    text_frame,
)
from greenmachine.inputs import (
    AbsenceReason,
    BatterInputs,
    PitchTypeSplit,
    Window,
    WindowedPitchTypeSplits,
)
from greenmachine.splits.eligibility import (
    DEFAULT_USAGE_THRESHOLD,
    Eligibility,
    EligibilityVerdict,
    classify_usage,
)

PITCH_TYPE_COLUMN = "Pitch type"

# Canonical metric order for this screen. Usage leads because it is the field
# eligibility is decided on, and a reader should see the number that decided
# the row's presence before the metrics that did not.
METRIC_COLUMNS: tuple[str, ...] = (
    "Usage %",
    "Barrel rate",
    "Exit velocity",
    "ISO",
    "xwOBA",
    "Whiff%",
    "SwStr%",
)

# Each metric's denominator, in the user's words. Displayed on the screen, not
# only carried in the data: criterion 4's legibility is a property of what the
# reader can see. The two swing/pitch denominators are spelled out at length
# precisely because their names are nearly the same.
DENOMINATORS: dict[str, str] = {
    "Usage %": "share of every tracked pitch of every type (not a filtered total)",
    "Barrel rate": "BBE — batted-ball events, home runs included (never BABIP)",
    "Exit velocity": "average over BBE — batted-ball events, home runs included",
    "ISO": "at-bats (not plate appearances — walks would deflate it)",
    "xwOBA": "plate appearances ending on this pitch type (not xwOBACON's BBE)",
    "Whiff%": "swings at this pitch type",
    "SwStr%": "pitches of this pitch type (not swings, and not all pitches)",
}

# The absence texts a reader sees for a metric that has no number, in words
# rather than as a blank or a null. Keyed to the contract's three reasons.
ABSENCE_WORDS: dict[AbsenceReason, str] = {
    AbsenceReason.NOT_APPLICABLE: "not applicable to this row",
    AbsenceReason.NOT_YET_OBSERVED: (
        "not yet observed — the source answered, nothing has accumulated"
    ),
    AbsenceReason.SOURCE_UNAVAILABLE: (
        "source unavailable — the source was consulted and did not answer"
    ),
}


def split_fields(split: PitchTypeSplit) -> dict[str, MetricField]:
    """One pitch type's seven metrics, keyed by their column names."""
    return {
        "Usage %": split.usage_share,
        "Barrel rate": split.barrel_rate,
        "Exit velocity": split.exit_velocity,
        "ISO": split.isolated_power,
        "xwOBA": split.expected_woba,
        "Whiff%": split.whiff_rate,
        "SwStr%": split.swinging_strike_rate,
    }


@dataclass(frozen=True)
class SuppressedType:
    """A pitch type the screen does not show, and exactly why."""

    pitch_type: str
    verdict: EligibilityVerdict


@dataclass(frozen=True)
class SplitScreen:
    """Everything the metrics screen renders for one batter in one window.

    ``set_absence`` is the level above every other state: when the split set
    itself is absent the screen says so with the reason, rather than rendering
    an empty table that would read as "no pitch types" — a claim nobody made.
    """

    window: Window
    threshold: Decimal
    set_absence: AbsenceReason | None
    qualifying: tuple[PitchTypeSplit, ...]
    below_threshold: tuple[SuppressedType, ...]
    unevaluable: tuple[SuppressedType, ...]

    @property
    def has_rows(self) -> bool:
        return bool(self.qualifying)

    @property
    def observed_no_pitches(self) -> bool:
        """The present-but-empty set: the source answered and this batter faced
        no tracked pitches. A real observation, and not the same as absence."""
        return (
            self.set_absence is None
            and not self.qualifying
            and not self.below_threshold
            and not self.unevaluable
        )


def build_screen(
    windowed: WindowedPitchTypeSplits, threshold: Decimal = DEFAULT_USAGE_THRESHOLD
) -> SplitScreen:
    """Sort every pitch type into shown, suppressed, or unevaluable.

    The window is taken from ``windowed.window`` and never from a caller's
    parameter, so the window this screen names is necessarily the window that
    produced its rows.
    """
    splits = windowed.splits.value
    if splits is None:
        assert windowed.splits.absence is not None  # the contract's exactly-one law
        return SplitScreen(
            window=windowed.window,
            threshold=threshold,
            set_absence=windowed.splits.absence,
            qualifying=(),
            below_threshold=(),
            unevaluable=(),
        )
    # Neutral identity order — the pitch type's own name. Never usage order:
    # ordering rows by a metric is the product choosing what matters, which is
    # the user's job in the column headers (D-015/D-017).
    ordered = sorted(splits, key=lambda split: split.pitch_type)
    qualifying: list[PitchTypeSplit] = []
    below: list[SuppressedType] = []
    unevaluable: list[SuppressedType] = []
    for split in ordered:
        verdict = classify_usage(split.usage_share, threshold)
        if verdict.eligibility is Eligibility.QUALIFIES:
            qualifying.append(split)
        elif verdict.eligibility is Eligibility.BELOW_THRESHOLD:
            below.append(SuppressedType(split.pitch_type, verdict))
        else:
            unevaluable.append(SuppressedType(split.pitch_type, verdict))
    return SplitScreen(
        window=windowed.window,
        threshold=threshold,
        set_absence=None,
        qualifying=tuple(qualifying),
        below_threshold=tuple(below),
        unevaluable=tuple(unevaluable),
    )


def screen_rows(screen: SplitScreen) -> list[FieldRow]:
    """The qualifying pitch types as grid rows."""
    return [(split.pitch_type, split_fields(split)) for split in screen.qualifying]


def screen_frames(screen: SplitScreen) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The numeric, text and style frames the component receives.

    All three come from the §GMF-002 builders; only the rows and columns differ.
    """
    rows = screen_rows(screen)
    return (
        numeric_frame(rows, PITCH_TYPE_COLUMN, METRIC_COLUMNS),
        text_frame(rows, PITCH_TYPE_COLUMN, METRIC_COLUMNS),
        style_frame_for(rows, PITCH_TYPE_COLUMN, METRIC_COLUMNS),
    )


def screen_state_frame(screen: SplitScreen) -> pd.DataFrame:
    """The display-state tokens behind each cell — the testable semantics."""
    return display_state_frame(screen_rows(screen), PITCH_TYPE_COLUMN, METRIC_COLUMNS)


def window_label(screen: SplitScreen) -> str:
    """The window named in the UI, read off the data that produced the rows."""
    return screen.window.value


def threshold_statement(screen: SplitScreen) -> str:
    """Criterion 3's threshold, stated on the screen as a percentage."""
    percent = screen.threshold * Decimal("100")
    return f"Pitch types are shown at or above {percent.normalize()}% usage share."


def suppression_notes(screen: SplitScreen) -> tuple[str, ...]:
    """The suppressed types, acknowledged by name — never a silent drop, and
    never a bare count without the names it stands for.

    The two groups stay apart: a type below the threshold was measured and
    found small, while an unevaluable type was never measured at all. Merging
    them would report a share nobody observed.
    """
    notes: list[str] = []
    if screen.below_threshold:
        named = ", ".join(
            f"{item.pitch_type} ({item.verdict.share})" for item in screen.below_threshold
        )
        count = len(screen.below_threshold)
        notes.append(f"Below the threshold, measured and suppressed ({count}): {named}.")
    if screen.unevaluable:
        named = ", ".join(
            f"{item.pitch_type} ({ABSENCE_WORDS[item.verdict.absence]})"
            for item in screen.unevaluable
            if item.verdict.absence is not None
        )
        notes.append(
            f"Usage never observed, so eligibility is unevaluable rather than "
            f"below threshold ({len(screen.unevaluable)}): {named}."
        )
    return tuple(notes)


def absence_notes(screen: SplitScreen) -> tuple[str, ...]:
    """Every absent metric on a shown row, named with its reason **in words**.

    This exists because of a defect observed on the canvas rather than inferred:
    the deployed component renders a null-data cell as its own ``None`` and
    discards the Styler's display value there, so a cell whose payload correctly
    says "source unavailable" still reads as ``None`` and the three absence
    states survive visually only as background colours. The payload is right and
    the render is not, and the same behaviour reproduces here because this screen
    is built on the same component (which is the point of criterion 5).

    The remedy is the one D-058 established for the batter grid: put the reason
    somewhere it can be read. This is a text surface on §GMF-003's own screen,
    not a change to how any cell renders — the grid-cell representation is
    untouched.
    """
    notes: list[str] = []
    for split in screen.qualifying:
        missing = [
            f"{column} ({ABSENCE_WORDS[field.absence]})"
            for column, field in split_fields(split).items()
            if field.absence is not None
        ]
        if missing:
            notes.append(f"{split.pitch_type} — {'; '.join(missing)}")
    return tuple(notes)


def denominator_notes() -> tuple[str, ...]:
    """Each metric with the denominator it is over, in the canonical order."""
    return tuple(f"{column} — {DENOMINATORS[column]}" for column in METRIC_COLUMNS)


def provenance_notes(screen: SplitScreen) -> tuple[str, ...]:
    """Per metric, per row: which values are derived, and which are sourced.

    Read off the fields themselves — a value with no recorded derivation came
    from the source; one with a derivation is a computation this product made.

    **The statement is per row, never a column-level summary.** This function's
    first version gathered every formula in a column and emitted one line —
    `Whiff% — derived: <formula>` — which collapsed the mixed state: with one
    derived Whiff% beside two sourced ones, a computed number sat next to
    sourced numbers looking identical, and the note said neither which row was
    derived nor that the others were not. The distinction the contract preserves
    per field (`SnapshotField.derivation`) was being flattened at exactly the
    point of presentation. So a mixed state now names the rows on **both**
    sides: the derived rows with their formulas, and the sourced rows by name —
    an explicit complement, not an implied one.
    """
    notes: list[str] = []
    for column in METRIC_COLUMNS:
        derived: list[tuple[str, str]] = []
        sourced: list[str] = []
        for pitch_type, fields_by_column in screen_rows(screen):
            derivation = fields_by_column[column].derivation
            if derivation is None:
                sourced.append(pitch_type)
            else:
                derived.append((pitch_type, derivation.formula))
        if not derived:
            notes.append(f"{column} — from source for every shown pitch type, not computed")
        elif not sourced:
            per_row = "; ".join(f"{pitch_type}: {formula}" for pitch_type, formula in derived)
            notes.append(f"{column} — derived for every shown pitch type — {per_row}")
        else:
            per_row = "; ".join(f"{pitch_type} ({formula})" for pitch_type, formula in derived)
            notes.append(
                f"{column} — MIXED: derived for {per_row}; from source for {', '.join(sourced)}"
            )
    return tuple(notes)


def absent_metric_notes(batter: BatterInputs, window: Window) -> tuple[str, ...]:
    """The selection-driven detail content (D-058): every grid metric's state
    for the selected batter, in words.

    This is the authorized remedy for the recorded GMF-002 defect in which an
    absent cell renders on the deployed canvas as the component's own null.
    The grid's payload was always correct; what was missing was somewhere the
    reason could be *read*. Present metrics show their value with its sample,
    so the panel is a complete account of the row rather than a list of what
    went wrong.
    """
    return tuple(
        f"{column} — {cell_text(field)}"
        for column, field in metric_fields(batter.metrics_for(window)).items()
    )
