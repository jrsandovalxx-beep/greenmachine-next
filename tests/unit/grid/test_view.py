"""GMF-002 direct tests: the grid's view logic as ordinary code (D-061).

These tests prove the pure half of the boundary — frames, absence rendering,
grading, visibility, density — with no Streamlit in sight. The AppTest half
(`tests/app/test_grid_page.py`) proves what the composition root hands the
element; nothing anywhere claims to synthesize a click.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from greenmachine.fixtures import grid_demo_snapshot
from greenmachine.fixtures.grid_demo import SOURCE_ID
from greenmachine.grid import (
    ABSENCE_TEXT,
    BATTER_COLUMN,
    DENSITY_ROWS,
    METRIC_COLUMNS,
    frame_height,
    graded_styler,
    grid_frame,
    row_batter_ids,
    state_frame,
    style_lookup,
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
# The display frame: neutral order, no blanks, absence texts with teeth
# ---------------------------------------------------------------------------


def test_initial_row_order_is_neutral_identity_order() -> None:
    """Sort, don't blend: the first render orders by batter name, never a
    metric. Every metric ordering is user-initiated in the component."""
    display = grid_frame(SNAPSHOT, Window.RECENT_7D)
    names = list(display[BATTER_COLUMN])
    assert names == sorted(names)
    assert names[0] == "Batter Alpha"


def test_no_cell_is_ever_blank() -> None:
    for window in Window:
        display = grid_frame(SNAPSHOT, window)
        for column in display.columns:
            for cell in display[column]:
                assert isinstance(cell, str) and cell.strip(), (
                    f"blank cell in {column!r} at window {window.value}"
                )


def test_absence_texts_are_distinct_from_each_other_and_from_every_value() -> None:
    """The criterion with teeth: three absence texts, mutually distinct, and
    no present rendering — the true zero included — collides with any."""
    absence_texts = set(ABSENCE_TEXT.values())
    assert len(absence_texts) == 3
    display = grid_frame(SNAPSHOT, Window.RECENT_7D)
    states = state_frame(SNAPSHOT, Window.RECENT_7D)
    for column in METRIC_COLUMNS:
        for cell, state in zip(display[column], states[column], strict=True):
            if state == "value":
                assert cell not in absence_texts
            else:
                assert cell in absence_texts


def test_a_true_zero_renders_as_a_number_with_its_sample_beside_it() -> None:
    """Batter Bravo's zero barrel rate over six BBE: a present observation —
    a number and its denominator (D-014), never a blank, never absence text."""
    display = grid_frame(SNAPSHOT, Window.RECENT_7D)
    bravo = display[display[BATTER_COLUMN] == "Batter Bravo"].iloc[0]
    assert bravo["Barrel rate"] == "0 · BBE 6"
    assert bravo["Ideal attack angle"] == "0 · swings 7"


def test_every_absence_state_appears_in_the_demo_frame_distinctly() -> None:
    display = grid_frame(SNAPSHOT, Window.RECENT_7D)
    by_name = display.set_index(BATTER_COLUMN)
    assert by_name.loc["Batter Charlie", "Barrel rate"] == "not yet observed"
    assert by_name.loc["Batter Delta", "Barrel rate"] == "source unavailable"
    assert by_name.loc["Batter Echo", "Barrel rate"] == "not applicable"


def test_switching_windows_changes_present_data() -> None:
    seven = grid_frame(SNAPSHOT, Window.RECENT_7D).set_index(BATTER_COLUMN)
    fourteen = grid_frame(SNAPSHOT, Window.RECENT_14D).set_index(BATTER_COLUMN)
    assert seven.loc["Batter Alpha", "Barrel rate"] == "0.900 · BBE 4"
    assert fourteen.loc["Batter Alpha", "Barrel rate"] == "0.500 · BBE 4"


def test_state_frame_mirrors_the_contract_display_states() -> None:
    """The state frame's identity column carries the token ``identity`` by
    design, so rows are addressed through the display frame's names — the two
    frames share row order by construction."""
    display = grid_frame(SNAPSHOT, Window.RECENT_7D)
    states = state_frame(SNAPSHOT, Window.RECENT_7D)
    assert set(states[BATTER_COLUMN]) == {"identity"}
    states = states.set_axis(display[BATTER_COLUMN], axis=0)
    assert set(states.loc["Batter Alpha", list(METRIC_COLUMNS)]) == {"value"}
    assert set(states.loc["Batter Charlie", list(METRIC_COLUMNS)]) == {"not_yet_observed"}
    assert set(states.loc["Batter Delta", list(METRIC_COLUMNS)]) == {"source_unavailable"}
    assert set(states.loc["Batter Echo", list(METRIC_COLUMNS)]) == {"not_applicable"}


# ---------------------------------------------------------------------------
# Grading: hand-rolled, green-is-good, absences never green
# ---------------------------------------------------------------------------


def test_absence_styles_are_mutually_distinct_and_never_green() -> None:
    lookup = style_lookup(SNAPSHOT, Window.RECENT_7D)
    column_map = lookup["Barrel rate"]
    styles = {reason: column_map[text] for reason, text in ABSENCE_TEXT.items()}
    assert len(set(styles.values())) == 3
    for style in styles.values():
        assert "rgb(" not in style  # the green scale is rgb(); absences never use it


def test_present_values_grade_within_their_column() -> None:
    """Alpha's 0.900 outgrades Bravo's zero; both carry the green scale; the
    zero still gets a style — pale is not blank."""
    lookup = style_lookup(SNAPSHOT, Window.RECENT_7D)
    column_map = lookup["Barrel rate"]
    strong = column_map["0.900 · BBE 4"]
    pale = column_map["0 · BBE 6"]
    assert strong != pale
    assert strong.startswith("color: #0a3622") and pale.startswith("color: #0a3622")
    assert "rgb(111, 183, 121)" in strong  # full intensity at the column max
    assert "rgb(233, 247, 233)" in pale  # palest green at the column min


def test_the_styler_applies_the_lookup_via_map() -> None:
    """D-059's named mechanism, exercised end to end: the rendered HTML
    carries the absence styles and the graded greens — no matplotlib."""
    display = grid_frame(SNAPSHOT, Window.RECENT_7D)
    styler = graded_styler(display, style_lookup(SNAPSHOT, Window.RECENT_7D))
    html = styler.to_html()
    assert "background-color: #fff3cd" in html  # not yet observed
    assert "background-color: #f8d7da" in html  # source unavailable
    assert "background-color: #e9ecef" in html  # not applicable
    assert "rgb(111, 183, 121)" in html  # the strongest green in the frame


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
