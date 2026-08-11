"""GMF-002 direct tests: the grid's view logic as ordinary code (D-061).

These tests prove the pure half of the boundary — the numeric data frame,
display texts, absence rendering, grading, visibility, density — with no
Streamlit in sight. The AppTest half (`tests/app/test_grid_page.py`) proves
what the composition root hands the element; nothing anywhere claims to
synthesize a click.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from greenmachine.fixtures import grid_demo_snapshot
from greenmachine.fixtures.grid_demo import SOURCE_ID
from greenmachine.grid import (
    ABSENCE_TEXT,
    BATTER_COLUMN,
    DENSITY_ROWS,
    METRIC_COLUMNS,
    display_texts,
    frame_height,
    graded_styler,
    grid_frame,
    row_batter_ids,
    state_frame,
    style_frame,
    visible_columns,
)
from greenmachine.inputs import AbsenceReason, Window

SNAPSHOT = grid_demo_snapshot()

SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "greenmachine"


# ---------------------------------------------------------------------------
# The boundary itself: the grid and fixtures packages import no streamlit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    sorted((SRC_ROOT / "grid").glob("*.py")) + sorted((SRC_ROOT / "fixtures").glob("*.py")),
    ids=lambda p: p.name,
)
def test_the_pure_side_of_the_boundary_imports_no_streamlit(module: Path) -> None:
    """D-061 as an architecture line: widgets live in the composition root
    only, so everything here stays provable as ordinary code."""
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            assert not name.startswith("streamlit"), f"{module.name} imports {name}"


# ---------------------------------------------------------------------------
# The data frame: numeric metrics (the sort substrate), neutral order
# ---------------------------------------------------------------------------


def test_metric_columns_are_numeric_so_the_component_sorts_numerically() -> None:
    """Finding-2 repair at its root: the component sorts on the data payload,
    so the data payload must be numeric. A regression to string metric
    columns fails here before it can sort lexicographically anywhere."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D)
    for column in METRIC_COLUMNS:
        assert pd.api.types.is_float_dtype(data[column]), f"{column} is not numeric"


def test_the_sort_divergence_pair_orders_numerically_not_textually() -> None:
    """The reviewer's divergence case: textual and numeric order disagree on
    the exit-velocity column (1000.5 vs 950.5 straddles a digit-count
    boundary), so a lexicographic implementation cannot pass by accident."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D)
    ev = data["Exit velocity"].dropna()
    numeric_order = list(ev.sort_values().index)
    textual_order = list(ev.astype(str).sort_values().index)
    assert numeric_order != textual_order, "the fixture no longer exposes the divergence"
    texts = display_texts(SNAPSHOT, Window.RECENT_7D)
    shown = [texts.loc[i, "Exit velocity"] for i in numeric_order]
    assert shown == ["950.5 mph · BBE 6", "1000.5 mph · BBE 4"]


def test_initial_row_order_is_neutral_identity_order() -> None:
    """Sort, don't blend: the first render orders by batter name, never a
    metric. Every metric ordering is user-initiated in the component."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D)
    names = list(data[BATTER_COLUMN])
    assert names == sorted(names)
    assert names[0] == "Batter Alpha"


def test_absences_are_missing_in_data_and_named_in_text() -> None:
    """One absence fact, two payloads: missing in the numeric data (so it
    sorts as absent, never as zero) and a named reason in the display text."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D).set_index(BATTER_COLUMN)
    texts = display_texts(SNAPSHOT, Window.RECENT_7D).set_index(BATTER_COLUMN)
    for name, reason in [
        ("Batter Charlie", AbsenceReason.NOT_YET_OBSERVED),
        ("Batter Delta", AbsenceReason.SOURCE_UNAVAILABLE),
        ("Batter Echo", AbsenceReason.NOT_APPLICABLE),
    ]:
        for column in METRIC_COLUMNS:
            assert pd.isna(data.loc[name, column])
            assert texts.loc[name, column] == ABSENCE_TEXT[reason]


def test_a_true_zero_is_numeric_zero_with_its_sample_in_the_text() -> None:
    """Batter Bravo: 0.0 in the data — a value that sorts as a value — and
    `0 · BBE 6` in the display (D-014), never a blank, never absence text."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D).set_index(BATTER_COLUMN)
    texts = display_texts(SNAPSHOT, Window.RECENT_7D).set_index(BATTER_COLUMN)
    assert data.loc["Batter Bravo", "Barrel rate"] == 0.0
    assert texts.loc["Batter Bravo", "Barrel rate"] == "0 · BBE 6"
    assert texts.loc["Batter Bravo", "Ideal attack angle"] == "0 · swings 7"


def test_no_display_text_is_ever_blank() -> None:
    for window in Window:
        texts = display_texts(SNAPSHOT, window)
        for column in texts.columns:
            for cell in texts[column]:
                assert isinstance(cell, str) and cell.strip(), (
                    f"blank cell in {column!r} at window {window.value}"
                )


def test_absence_texts_are_distinct_from_each_other_and_from_every_value() -> None:
    absence_texts = set(ABSENCE_TEXT.values())
    assert len(absence_texts) == 3
    texts = display_texts(SNAPSHOT, Window.RECENT_7D)
    states = state_frame(SNAPSHOT, Window.RECENT_7D)
    for column in METRIC_COLUMNS:
        for cell, state in zip(texts[column], states[column], strict=True):
            if state == "value":
                assert cell not in absence_texts
            else:
                assert cell in absence_texts


def test_switching_windows_changes_present_data() -> None:
    seven = grid_frame(SNAPSHOT, Window.RECENT_7D).set_index(BATTER_COLUMN)
    fourteen = grid_frame(SNAPSHOT, Window.RECENT_14D).set_index(BATTER_COLUMN)
    assert seven.loc["Batter Alpha", "Barrel rate"] == 0.9
    assert fourteen.loc["Batter Alpha", "Barrel rate"] == 0.5


def test_state_frame_mirrors_the_contract_display_states() -> None:
    """The state frame's identity column carries the token ``identity`` by
    design, so rows are addressed through the data frame's names — the two
    frames share row order by construction."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D)
    states = state_frame(SNAPSHOT, Window.RECENT_7D)
    assert set(states[BATTER_COLUMN]) == {"identity"}
    states = states.set_axis(data[BATTER_COLUMN], axis=0)
    assert set(states.loc["Batter Alpha", list(METRIC_COLUMNS)]) == {"value"}
    assert set(states.loc["Batter Charlie", list(METRIC_COLUMNS)]) == {"not_yet_observed"}
    assert set(states.loc["Batter Delta", list(METRIC_COLUMNS)]) == {"source_unavailable"}
    assert set(states.loc["Batter Echo", list(METRIC_COLUMNS)]) == {"not_applicable"}


# ---------------------------------------------------------------------------
# Grading: hand-rolled, green-is-good, absences never green, by position
# ---------------------------------------------------------------------------


def test_absence_styles_are_mutually_distinct_and_never_green() -> None:
    styles = style_frame(SNAPSHOT, Window.RECENT_7D).set_axis(
        grid_frame(SNAPSHOT, Window.RECENT_7D)[BATTER_COLUMN], axis=0
    )
    per_reason = {
        "Batter Echo": styles.loc["Batter Echo", "Barrel rate"],
        "Batter Charlie": styles.loc["Batter Charlie", "Barrel rate"],
        "Batter Delta": styles.loc["Batter Delta", "Barrel rate"],
    }
    assert len(set(per_reason.values())) == 3
    for style in per_reason.values():
        assert "rgb(" not in style  # the green scale is rgb(); absences never use it


def test_present_values_grade_within_their_column() -> None:
    """Alpha's 0.9 outgrades Bravo's zero; both carry the green scale; the
    zero still gets a style — pale is not blank."""
    styles = style_frame(SNAPSHOT, Window.RECENT_7D).set_axis(
        grid_frame(SNAPSHOT, Window.RECENT_7D)[BATTER_COLUMN], axis=0
    )
    strong = styles.loc["Batter Alpha", "Barrel rate"]
    pale = styles.loc["Batter Bravo", "Barrel rate"]
    assert strong != pale
    assert strong.startswith("color: #0a3622") and pale.startswith("color: #0a3622")
    assert "rgb(111, 183, 121)" in strong  # full intensity at the column max
    assert "rgb(233, 247, 233)" in pale  # palest green at the column min


def test_the_styler_carries_display_texts_and_styles_via_map() -> None:
    """D-059's named mechanism over the numeric frame: the rendered HTML
    carries every display text (values with samples, all three absence
    texts) and the graded and absence styles — no matplotlib."""
    data = grid_frame(SNAPSHOT, Window.RECENT_7D)
    styler = graded_styler(
        data,
        display_texts(SNAPSHOT, Window.RECENT_7D),
        style_frame(SNAPSHOT, Window.RECENT_7D),
    )
    html = styler.to_html()
    for needle in (
        "0 · BBE 6",
        "1000.5 mph · BBE 4",
        "950.5 mph · BBE 6",
        "not applicable",
        "not yet observed",
        "source unavailable",
        "background-color: #fff3cd",
        "background-color: #f8d7da",
        "background-color: #e9ecef",
        "rgb(111, 183, 121)",
    ):
        assert needle in html, needle


def test_matplotlib_is_not_installed_with_the_project() -> None:
    """D-059 negatively: the dependency the decision forbids is absent."""
    import importlib.util

    assert importlib.util.find_spec("matplotlib") is None


# ---------------------------------------------------------------------------
# Visibility and density
# ---------------------------------------------------------------------------


def test_the_identity_column_always_shows_and_order_is_canonical() -> None:
    assert visible_columns(()) == [BATTER_COLUMN]
    assert visible_columns(("Pull air", "Barrel rate")) == [
        BATTER_COLUMN,
        "Barrel rate",
        "Pull air",
    ]


def test_density_presets_map_to_deterministic_heights() -> None:
    assert set(DENSITY_ROWS) == {"Compact", "Cozy", "Roomy"}
    assert frame_height("Compact", 5) == 38 + 35 * 4 + 3
    assert frame_height("Cozy", 5) == 38 + 35 * 5 + 3  # capped at the data
    assert frame_height("Roomy", 20) == 38 + 35 * 14 + 3


def test_row_batter_ids_follow_the_neutral_order() -> None:
    assert row_batter_ids(SNAPSHOT) == (
        "grid-demo-1",
        "grid-demo-2",
        "grid-demo-3",
        "grid-demo-4",
        "grid-demo-5",
    )


def test_the_fixture_names_its_single_synthetic_source() -> None:
    """OQ-4 and the source rule together: every field resolves to the one
    declared synthetic source — the deployed page renders no provider data."""
    assert [record.source_id for record in SNAPSHOT.sources] == [SOURCE_ID]
    for owner, field in SNAPSHOT.iter_fields():
        assert field.source_id == SOURCE_ID, owner


def test_every_absence_reason_is_reachable_in_the_fixture() -> None:
    reasons = {field.absence for _, field in SNAPSHOT.iter_fields() if field.absence is not None}
    assert reasons == set(AbsenceReason)
