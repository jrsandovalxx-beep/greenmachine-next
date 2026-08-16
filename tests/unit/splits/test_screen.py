"""The §GMF-003 metrics screen, criterion by criterion.

The screen is proved here as ordinary code, which is D-061's boundary applied to
a second surface: AppTest cannot synthesize the row selection that opens this
panel at the 1.37 floor, so what the panel computes is direct-tested and what the
page hands the component is asserted in ``tests/app``.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from greenmachine.fixtures import grid_demo_snapshot
from greenmachine.grid import batter_for
from greenmachine.inputs import AbsenceReason, SnapshotField, Window
from greenmachine.splits import (
    DENOMINATORS,
    METRIC_COLUMNS,
    PITCH_TYPE_COLUMN,
    SplitScreen,
    absence_notes,
    absent_metric_notes,
    build_screen,
    denominator_notes,
    provenance_notes,
    screen_frames,
    screen_state_frame,
    split_fields,
    suppression_notes,
    threshold_statement,
    window_label,
)

SNAPSHOT = grid_demo_snapshot()
ALPHA = batter_for(SNAPSHOT, "grid-demo-1")  # every eligibility state
BRAVO = batter_for(SNAPSHOT, "grid-demo-2")  # present, empty split set
CHARLIE = batter_for(SNAPSHOT, "grid-demo-3")  # set absent NOT_YET_OBSERVED
DELTA = batter_for(SNAPSHOT, "grid-demo-4")  # set absent SOURCE_UNAVAILABLE
ECHO = batter_for(SNAPSHOT, "grid-demo-5")  # set absent NOT_APPLICABLE


def _screen(batter=ALPHA):  # type: ignore[no-untyped-def]
    return build_screen(batter.splits_for(Window.SEASON_TO_DATE))


# ---------------------------------------------------------------------------
# Criterion 2 — the window is current season, named, not implied
# ---------------------------------------------------------------------------


def test_the_screen_names_the_season_window() -> None:
    assert window_label(_screen()) == "SEASON_TO_DATE"


def test_the_window_label_is_read_off_the_data_that_produced_the_rows() -> None:
    """Not from a caller's argument and not from a UI constant: ``build_screen``
    takes no window parameter, so the label cannot disagree with the rows."""
    for window in Window:
        screen = build_screen(ALPHA.splits_for(window))
        assert window_label(screen) == window.value


# ---------------------------------------------------------------------------
# Criterion 3 — the threshold, stated; suppression, acknowledged; three states
# ---------------------------------------------------------------------------


def test_the_threshold_is_stated_on_the_screen_as_a_percentage() -> None:
    assert threshold_statement(_screen()) == "Pitch types are shown at or above 15% usage share."


def test_only_types_at_or_above_the_threshold_are_shown() -> None:
    screen = _screen()
    assert [split.pitch_type for split in screen.qualifying] == ["CH", "FF", "SL"]


def test_rows_are_in_neutral_identity_order_not_usage_order() -> None:
    """D-015/D-017: the product does not rank. CH (0.160) precedes FF (0.550)
    because C precedes F, which usage order would reverse."""
    shown = [split.pitch_type for split in _screen().qualifying]
    assert shown == sorted(shown)
    assert shown[0] == "CH"


def test_suppressed_types_are_named_never_a_bare_count() -> None:
    notes = " ".join(suppression_notes(_screen()))
    for pitch_type in ("CU", "SI"):
        assert pitch_type in notes
    assert "2" in notes  # the count travels with the names, not instead of them


def test_a_true_zero_share_is_suppressed_as_a_measurement() -> None:
    """SI was thrown zero times over a positive sample — observed, not missing."""
    screen = _screen()
    zero = next(item for item in screen.below_threshold if item.pitch_type == "SI")
    assert zero.verdict.share == Decimal("0")
    assert zero.verdict.absence is None


def test_unevaluable_types_are_separated_from_below_threshold_ones() -> None:
    """The distinction criterion 3 needs: KC and FS were never measured, so
    calling them "below threshold" would assert a share nobody observed."""
    screen = _screen()
    assert {item.pitch_type for item in screen.unevaluable} == {"KC", "FS"}
    assert {item.pitch_type for item in screen.below_threshold} == {"CU", "SI"}
    notes = suppression_notes(screen)
    assert any("unevaluable" in note for note in notes)
    assert any("Below the threshold" in note for note in notes)


def test_each_unevaluable_reason_stays_distinct() -> None:
    """Not flattened to "unknown": KC's source answered, FS's did not."""
    screen = _screen()
    reasons = {item.pitch_type: item.verdict.absence for item in screen.unevaluable}
    assert reasons == {
        "KC": AbsenceReason.NOT_YET_OBSERVED,
        "FS": AbsenceReason.SOURCE_UNAVAILABLE,
    }
    notes = " ".join(suppression_notes(screen))
    assert "not yet observed" in notes
    assert "source unavailable" in notes


def test_a_qualifying_type_with_one_missing_metric_keeps_its_row() -> None:
    """Eligibility and availability, separated where it matters: SL is missing
    its xwOBA and is still displayed, with that one cell naming its reason."""
    screen = _screen()
    assert "SL" in [split.pitch_type for split in screen.qualifying]
    states = screen_state_frame(screen)
    row = states[states[PITCH_TYPE_COLUMN] == "identity"]
    _numeric, texts, _styles = screen_frames(screen)
    sl_index = [split.pitch_type for split in screen.qualifying].index("SL")
    assert texts.at[sl_index, "xwOBA"] == "source unavailable"
    assert texts.at[sl_index, "Barrel rate"] != "source unavailable"
    assert len(row) == len(screen.qualifying)


# ---------------------------------------------------------------------------
# Criterion 4 — every metric's denominator legible
# ---------------------------------------------------------------------------


def test_every_metric_states_a_denominator() -> None:
    assert set(DENOMINATORS) == set(METRIC_COLUMNS)
    assert len(denominator_notes()) == len(METRIC_COLUMNS)


def test_batted_ball_rates_name_bbe_and_never_babip() -> None:
    notes = " ".join(denominator_notes())
    assert "BBE" in notes
    assert "home runs included" in notes
    assert "never BABIP" in notes


def test_whiff_and_swinging_strike_denominators_are_not_interchangeable() -> None:
    """The named trap: same numerator, different denominators. The screen must
    not let one read as the other."""
    assert DENOMINATORS["Whiff%"] != DENOMINATORS["SwStr%"]
    assert "swings" in DENOMINATORS["Whiff%"]
    assert "pitches of this pitch type" in DENOMINATORS["SwStr%"]
    assert "not swings" in DENOMINATORS["SwStr%"]


def test_usage_names_the_unfiltered_pitch_total() -> None:
    """The second trap: usage's denominator spans every type, and the screen
    says so rather than leaving a filtered total to be assumed."""
    assert "every tracked pitch of every type" in DENOMINATORS["Usage %"]
    assert "not a filtered total" in DENOMINATORS["Usage %"]


def test_each_cell_carries_its_own_denominator_count() -> None:
    _numeric, texts, _styles = screen_frames(_screen())
    ff = [split.pitch_type for split in _screen().qualifying].index("FF")
    assert texts.at[ff, "Usage %"].endswith("pitches, all types")
    assert texts.at[ff, "SwStr%"].endswith("pitches, this type")
    assert "swings" in texts.at[ff, "Whiff%"]
    assert "BBE" in texts.at[ff, "Barrel rate"]
    assert "AB" in texts.at[ff, "ISO"]
    assert "PA" in texts.at[ff, "xwOBA"]


# ---------------------------------------------------------------------------
# Sourced versus derived — stated from the data
# ---------------------------------------------------------------------------


def test_every_metric_states_its_provenance() -> None:
    notes = provenance_notes(_screen())
    assert len(notes) == len(METRIC_COLUMNS)
    assert all("from source for every shown pitch type" in note for note in notes)
    assert not any("MIXED" in note for note in notes)


def _with_derived_whiff(screen: SplitScreen, row_index: int) -> SplitScreen:
    """The given screen with one row's Whiff% replaced by a derived value —
    the mixed state the first provenance implementation collapsed."""
    original = screen.qualifying[row_index]
    derived_field = SnapshotField.derived(
        original.whiff_rate.value,
        formula="swinging strikes / swings",
        inputs=("some other field",),
        source_id="grid-demo-synthetic",
    )
    patched = dataclasses.replace(original, whiff_rate=derived_field)
    qualifying = list(screen.qualifying)
    qualifying[row_index] = patched
    return dataclasses.replace(screen, qualifying=tuple(qualifying))


def test_a_mixed_column_identifies_the_derived_row_and_the_sourced_rows() -> None:
    """The property, not the text: with one derived Whiff% beside two sourced
    ones, the derived row must be identifiable by name AND the sourced rows
    must be identifiable as sourced by name. The first implementation emitted
    one column-level line, which passed a text-presence test while collapsing
    exactly this distinction — a computed number sitting beside sourced numbers
    looking identical. This test fails against that implementation."""
    screen = _with_derived_whiff(_screen(), 0)  # CH is row 0 of (CH, FF, SL)
    whiff_note = next(note for note in provenance_notes(screen) if note.startswith("Whiff%"))
    # The derived row, by name, with its formula attached to that name.
    assert "MIXED" in whiff_note
    assert "CH (swinging strikes / swings)" in whiff_note
    # The sourced rows, by name, as an explicit complement — not an implication.
    assert "from source for FF, SL" in whiff_note
    # And the derived claim must not leak onto the sourced rows' names.
    derived_clause = whiff_note.split("from source for", 1)[0]
    assert "FF" not in derived_clause
    assert "SL" not in derived_clause


def test_a_mixed_state_in_one_column_does_not_touch_the_others() -> None:
    """The mixed statement is per column: deriving one Whiff% says nothing
    about ISO, xwOBA, or any other column's provenance."""
    screen = _with_derived_whiff(_screen(), 1)
    notes = provenance_notes(screen)
    mixed = [note for note in notes if "MIXED" in note]
    assert len(mixed) == 1
    assert mixed[0].startswith("Whiff%")
    assert sum("from source for every shown pitch type" in note for note in notes) == (
        len(METRIC_COLUMNS) - 1
    )


def test_an_all_derived_column_names_every_row_with_its_formula() -> None:
    """The third state: every shown value computed. Not "MIXED" — there is no
    sourced complement to name — and still per-row, so two rows derived by the
    same formula cannot blur into one anonymous claim."""
    screen = _screen()
    for index in range(len(screen.qualifying)):
        screen = _with_derived_whiff(screen, index)
    whiff_note = next(note for note in provenance_notes(screen) if note.startswith("Whiff%"))
    assert "derived for every shown pitch type" in whiff_note
    for pitch_type in ("CH", "FF", "SL"):
        assert f"{pitch_type}: swinging strikes / swings" in whiff_note
    assert "MIXED" not in whiff_note


# ---------------------------------------------------------------------------
# The set-level states, one level above any metric
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("batter", "reason"),
    [
        (CHARLIE, AbsenceReason.NOT_YET_OBSERVED),
        (DELTA, AbsenceReason.SOURCE_UNAVAILABLE),
        (ECHO, AbsenceReason.NOT_APPLICABLE),
    ],
)
def test_an_absent_split_set_reports_its_reason_rather_than_an_empty_table(
    batter: object, reason: AbsenceReason
) -> None:
    screen = build_screen(batter.splits_for(Window.SEASON_TO_DATE))  # type: ignore[attr-defined]
    assert screen.set_absence is reason
    assert not screen.has_rows
    assert not screen.observed_no_pitches  # absent is not "observed nothing"


def test_a_present_empty_set_is_an_observation_not_an_absence() -> None:
    screen = _screen(BRAVO)
    assert screen.set_absence is None
    assert screen.observed_no_pitches
    assert not screen.has_rows


# ---------------------------------------------------------------------------
# Criterion 5 — built on the GMF-002 grid
# ---------------------------------------------------------------------------


def test_the_frames_come_from_the_grid_builders() -> None:
    """Same mechanism, different rows: the frames are positionally aligned and
    carry the identity column the grid's builders put there."""
    numeric, texts, styles = screen_frames(_screen())
    assert list(numeric.columns) == [PITCH_TYPE_COLUMN, *METRIC_COLUMNS]
    assert list(texts.columns) == list(numeric.columns)
    assert list(styles.columns) == list(numeric.columns)
    assert len(numeric) == len(texts) == len(styles) == 3


def test_metric_columns_are_numeric_so_the_component_sorts_numerically() -> None:
    numeric, _texts, _styles = screen_frames(_screen())
    for column in METRIC_COLUMNS:
        assert numeric[column].dtype == "float64"


def test_an_absent_cell_is_missing_data_with_its_reason_as_text() -> None:
    """The same absence discipline the grid carries: never blank, never zero."""
    numeric, texts, _styles = screen_frames(_screen())
    sl = [split.pitch_type for split in _screen().qualifying].index("SL")
    assert numeric.at[sl, "xwOBA"] != numeric.at[sl, "xwOBA"]  # NaN, so it sorts apart from zero
    assert texts.at[sl, "xwOBA"] == "source unavailable"


def test_split_fields_covers_every_metric_column_exactly() -> None:
    fields = split_fields(_screen().qualifying[0])
    assert set(fields) == set(METRIC_COLUMNS)


# ---------------------------------------------------------------------------
# The D-058 detail content — absent reasons in words
# ---------------------------------------------------------------------------


def test_the_detail_panel_states_every_grid_metric_in_words() -> None:
    notes = absent_metric_notes(CHARLIE, Window.SEASON_TO_DATE)
    assert len(notes) == 4
    assert all("not yet observed" in note for note in notes)


def test_the_detail_panel_distinguishes_the_three_absence_reasons() -> None:
    """The recorded GMF-002 defect: on the deployed canvas all three render as
    the component's own null, leaving colour as the only difference. Here they
    are three different sentences."""
    words = {
        batter.name: absent_metric_notes(batter, Window.SEASON_TO_DATE)[0]
        for batter in (CHARLIE, DELTA, ECHO)
    }
    assert len(set(words.values())) == 3


def test_the_detail_panel_shows_present_values_with_their_samples() -> None:
    """A complete account of the row, not only a list of what is missing."""
    notes = absent_metric_notes(ALPHA, Window.SEASON_TO_DATE)
    assert any("BBE" in note for note in notes)


# ---------------------------------------------------------------------------
# The absent-cell remedy, on this screen's own rows
# ---------------------------------------------------------------------------


def test_absent_metrics_on_shown_rows_are_named_in_words() -> None:
    """The component renders a null-data cell as its own ``None`` and drops the
    display value carried for it — observed on the local render, and reproduced
    here because this screen is built on the same component. The reason is
    therefore also stated as text."""
    notes = absence_notes(_screen())
    assert len(notes) == 1
    assert notes[0].startswith("SL — xwOBA")
    assert "source unavailable" in notes[0]


def test_rows_with_every_metric_present_produce_no_absence_note() -> None:
    """The note is evidence, not decoration: it appears only where a cell is
    genuinely absent."""
    screen = _screen()
    complete = [split for split in screen.qualifying if split.pitch_type != "SL"]
    assert absence_notes(dataclasses.replace(screen, qualifying=tuple(complete))) == ()
