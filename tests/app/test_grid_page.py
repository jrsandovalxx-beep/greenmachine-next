"""GMF-002 AppTest coverage: what the composition root hands the element.

D-061's boundary, kept exactly: AppTest proves the element's handed-off data
and the page's widget state — column set and order, the absence renderings
present **as data**, the graded values, the density and visibility controls'
states. The selection-consumption path is proven by direct tests
(`tests/unit/grid/test_selection.py`), because **AppTest cannot synthesize a
row selection at the 1.37 floor** — selection state is not programmatically
settable. And state coverage is not a rendering check: no assertion here
claims a gradient is legible. The click-to-detail interaction and visual
legibility are observed at §GMF-002 submission 2 on the deployed page.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from streamlit.testing.v1 import AppTest

from greenmachine.grid import ABSENCE_TEXT, BATTER_COLUMN, METRIC_COLUMNS

# Absolute, so resolution cannot drift: inside the D-062 bound, streamlit
# moved `from_file`'s relative-path anchor from the working directory to the
# calling file — an absolute path is stable under both behaviours.
_APP_PATH = Path(__file__).resolve().parents[2] / "streamlit_app.py"

_TIMEOUT = 15


def _run_app() -> AppTest:
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _grid_data(at: AppTest) -> pd.DataFrame:
    """The data handed to the grid element, Styler or frame alike."""
    assert len(at.dataframe) == 1, "exactly one grid element on the page"
    value: Any = at.dataframe[0].value
    frame = getattr(value, "data", value)
    assert isinstance(frame, pd.DataFrame)
    return frame


def test_the_page_runs_and_renders_exactly_one_grid() -> None:
    at = _run_app()
    frame = _grid_data(at)
    assert list(frame.columns) == [BATTER_COLUMN, *METRIC_COLUMNS]
    assert len(frame) == 5


def test_the_handed_off_data_carries_every_display_state_distinctly() -> None:
    """Absence-versus-zero as data: the three absence texts and the true zero
    all reach the element, and no cell is blank."""
    frame = _grid_data(_run_app())
    cells = {str(cell) for column in frame.columns for cell in frame[column]}
    for text in ABSENCE_TEXT.values():
        assert text in cells
    assert "0 · BBE 6" in cells  # Bravo's true zero: a number with its sample
    assert all(str(c).strip() for column in frame.columns for c in frame[column])


def test_the_initial_order_is_neutral_and_no_ranking_widget_exists() -> None:
    """D-015/D-017 at the page level: identity order on first render, and no
    control anywhere ranks or selects batters for the user."""
    at = _run_app()
    frame = _grid_data(at)
    names = list(frame[BATTER_COLUMN])
    assert names == sorted(names)
    labels = [w.label for w in [*at.selectbox, *at.multiselect, *at.radio]]
    assert labels == ["Window", "Columns", "Density"]


def test_the_window_control_swaps_the_handed_off_data() -> None:
    at = _run_app()
    assert at.selectbox(key="grid_window").value == "RECENT_7D"
    before = _grid_data(at).set_index(BATTER_COLUMN)
    assert before.loc["Batter Alpha", "Barrel rate"] == "0.900 · BBE 4"
    at.selectbox(key="grid_window").select("RECENT_14D").run()
    assert not at.exception
    after = _grid_data(at).set_index(BATTER_COLUMN)
    assert after.loc["Batter Alpha", "Barrel rate"] == "0.500 · BBE 4"
    assert after.loc["Batter Charlie", "Barrel rate"] == "not yet observed"


def test_the_column_control_state_drives_visibility() -> None:
    """The widget state is the visibility input; its mapping to the element's
    column order is `visible_columns`, proven directly — the handed-off data
    keeps all columns, and the page passes the subset as configuration."""
    at = _run_app()
    assert at.multiselect(key="grid_columns").value == list(METRIC_COLUMNS)
    at.multiselect(key="grid_columns").set_value(["Exit velocity"]).run()
    assert not at.exception
    assert at.multiselect(key="grid_columns").value == ["Exit velocity"]
    assert list(_grid_data(at).columns) == [BATTER_COLUMN, *METRIC_COLUMNS]


def test_the_density_control_state_is_user_owned() -> None:
    at = _run_app()
    assert at.radio(key="grid_density").value == "Cozy"
    at.radio(key="grid_density").set_value("Compact").run()
    assert not at.exception
    assert at.radio(key="grid_density").value == "Compact"
    assert len(_grid_data(at)) == 5  # density never drops data, only viewport


def test_with_no_selection_the_page_invites_one_and_claims_nothing() -> None:
    """The no-selection state renders the invitation caption; the detail
    mechanism's resolution path is direct-tested, not clicked."""
    at = _run_app()
    captions = " | ".join(c.value for c in at.caption)
    assert "Select a row" in captions
    assert "GMF-003" in captions


def test_the_shell_fields_survive_beside_the_grid() -> None:
    """The deployment-verification fields (GMR-004) still render: the page
    gained a product surface without losing its verification surface."""
    at = _run_app()
    body = " | ".join(m.value for m in at.markdown)
    assert "**Environment:**" in body
    assert "**Version:**" in body
    assert "**Commit:**" in body
