"""GMF-002 AppTest coverage: the element boundary, asserted at the element.

D-061's boundary, kept exactly — and at the right surface this round: the
assertions below read the **element**, not the frame behind it. Probed facts
this file builds on (the probe outputs travel with the package):

- the element's ``.value`` is the data frame (this streamlit's Dataframe
  wrapper exposes no Styler at ``.value``); the Styler is observable at
  ``proto.arrow_data.styler`` — its CSS in ``styles``, its rendered text as
  a separate Arrow payload in ``display_values``;
- ``proto.column_order`` is the element's visibility configuration;
- the Dataframe proto carries **no widget-height field at this streamlit
  version** — it did at the 1.37 floor (probed: the 1.37 ``Arrow`` proto has
  ``height``); the height assertion below therefore runs where the field
  exists and **skips loudly** where it does not, and the gap is reported in
  the package rather than silently substituted.

The selection-consumption path is proven by direct tests
(`tests/unit/grid/test_selection.py`): AppTest cannot synthesize a row
selection at the 1.37 floor. And state coverage is not a rendering check: no
assertion here claims a gradient is legible. The click-to-detail interaction
and visual legibility are observed at §GMF-002 submission 2.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pytest
from streamlit.testing.v1 import AppTest

from greenmachine.grid import (
    ABSENCE_TEXT,
    BATTER_COLUMN,
    METRIC_COLUMNS,
    frame_height,
    visible_columns,
)

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


def _element(at: AppTest) -> Any:
    assert len(at.dataframe) == 1, "exactly one grid element on the page"
    return at.dataframe[0]


def _arrow_surface(proto: Any) -> Any:
    """The one schema-tolerant accessor: the message carrying the Arrow
    payloads (`data`, `styler`), resolved across both proto schemas.

    The Dataframe proto forked **inside the D-062 bound** — the third
    inside-the-bound float move this ticket has caught (after
    `AppTest.from_file`'s path anchor and the height field itself): at the
    1.37 floor the element proto *is* the Arrow message (`data`, `styler`,
    `height`, … sit directly on it); the float nests them under an
    `arrow_data` message and drops `height` entirely. Every element
    assertion resolves its surface here, so the committed suite executes at
    the floor D-061 anchors to *and* on the float CI resolves — whoever
    meets the fourth fork, extend this accessor, not the call sites.
    """
    field_names = {f.name for f in proto.DESCRIPTOR.fields}
    if "arrow_data" in field_names:
        return proto.arrow_data
    assert "styler" in field_names, "unrecognised Dataframe proto schema"
    return proto


def _height_surface(proto: Any) -> Any | None:
    """Where the widget height is observable, if anywhere: the proto itself
    at the 1.37 floor; nowhere on the float (the reported gap)."""
    for candidate in (proto, _arrow_surface(proto)):
        if "height" in {f.name for f in candidate.DESCRIPTOR.fields}:
            return candidate
    return None


def _element_data(at: AppTest) -> pd.DataFrame:
    """The raw data payload the component sorts on."""
    value: Any = _element(at).value
    frame = getattr(value, "data", value)
    assert isinstance(frame, pd.DataFrame)
    return frame


def _styler_payload(at: AppTest) -> tuple[str, pd.DataFrame]:
    """The element's Styler as serialized: (styles CSS, display-value frame)."""
    styler = _arrow_surface(_element(at).proto).styler
    display = pa.ipc.open_stream(io.BytesIO(styler.display_values)).read_all().to_pandas()
    return styler.styles, display


def test_the_page_runs_and_renders_exactly_one_grid() -> None:
    at = _run_app()
    frame = _element_data(at)
    assert list(frame.columns) == [BATTER_COLUMN, *METRIC_COLUMNS]
    assert len(frame) == 5


def test_the_element_data_is_numeric_so_header_sort_is_numeric() -> None:
    """Finding 2 at the element boundary: the payload the component sorts on
    is numeric, and the fixture's divergence pair is present in it — textual
    and numeric order disagree, so a lexicographic regression cannot pass."""
    frame = _element_data(_run_app())
    for column in METRIC_COLUMNS:
        assert pd.api.types.is_float_dtype(frame[column]), f"{column} not numeric at the element"
    ev = frame["Exit velocity"].dropna()
    assert list(ev.sort_values().index) != list(ev.astype(str).sort_values().index)
    assert set(ev) == {1000.5, 950.5}


def test_the_element_styler_carries_display_texts_for_every_state() -> None:
    """Finding 1: the Styler wrapper asserted at the element (its serialized
    form), not reduced past — every absence text, and the true zero with its
    sample, reach the element as display values over the numeric data."""
    _styles, display = _styler_payload(_run_app())
    cells = {str(cell) for column in display.columns for cell in display[column]}
    for text in ABSENCE_TEXT.values():
        assert text in cells
    assert "0 · BBE 6" in cells
    assert "1000.5 mph · BBE 4" in cells and "950.5 mph · BBE 6" in cells
    assert all(str(c).strip() for column in display.columns for c in display[column])


def test_the_element_styler_carries_the_graded_and_absence_styles() -> None:
    styles, _display = _styler_payload(_run_app())
    assert "rgb(111, 183, 121)" in styles  # strongest green in the frame
    assert "background-color: #fff3cd" in styles  # not yet observed
    assert "background-color: #f8d7da" in styles  # source unavailable
    assert "background-color: #e9ecef" in styles  # not applicable


def test_the_element_column_order_follows_the_visibility_control() -> None:
    """Finding 1: the visibility claim asserted at the element's own
    configuration — `column_order` equals `visible_columns(...)`'s output,
    before and after the multiselect changes."""
    at = _run_app()
    assert list(_element(at).proto.column_order) == visible_columns(tuple(METRIC_COLUMNS))
    at.multiselect(key="grid_columns").set_value(["Exit velocity"]).run()
    assert not at.exception
    assert list(_element(at).proto.column_order) == visible_columns(("Exit velocity",))
    assert list(_element_data(at).columns) == [BATTER_COLUMN, *METRIC_COLUMNS]


def test_the_element_height_follows_the_density_control_where_observable() -> None:
    """Finding 1, the density half: asserted at the element where the proto
    exposes height — which the 1.37 floor's proto does (probed) and this
    installed version's does not. The skip is loud by design: the gap is a
    reported plan question, never a silent substitution."""
    at = _run_app()
    if _height_surface(_element(at).proto) is None:
        pytest.skip(
            "this streamlit's Dataframe proto exposes no height field (probed: "
            "present at the 1.37 floor, absent here) — the density-height "
            "element assertion is unobservable at this version and reported "
            "in the GMF-002 submission-1 package"
        )
    at.radio(key="grid_density").set_value("Compact").run()
    assert not at.exception
    surface = _height_surface(_element(at).proto)
    assert surface is not None
    assert surface.height == frame_height("Compact", len(_element_data(at)))


def test_the_window_control_swaps_the_element_data_and_display() -> None:
    at = _run_app()
    assert at.selectbox(key="grid_window").value == "RECENT_7D"
    before = _element_data(at).set_index(BATTER_COLUMN)
    assert before.loc["Batter Alpha", "Barrel rate"] == 0.9
    at.selectbox(key="grid_window").select("RECENT_14D").run()
    assert not at.exception
    after = _element_data(at).set_index(BATTER_COLUMN)
    assert after.loc["Batter Alpha", "Barrel rate"] == 0.5
    _styles, display = _styler_payload(at)
    assert "3.5 mph · BBE 4" in {str(c) for c in display["Exit velocity"]}


def test_the_density_control_state_is_user_owned() -> None:
    at = _run_app()
    assert at.radio(key="grid_density").value == "Cozy"
    at.radio(key="grid_density").set_value("Compact").run()
    assert not at.exception
    assert at.radio(key="grid_density").value == "Compact"
    assert len(_element_data(at)) == 5  # density never drops data, only viewport


def test_the_initial_order_is_neutral_and_no_ranking_widget_exists() -> None:
    """D-015/D-017 at the page level: identity order on first render, and no
    control anywhere ranks or selects batters for the user."""
    at = _run_app()
    frame = _element_data(at)
    names = list(frame[BATTER_COLUMN])
    assert names == sorted(names)
    labels = [w.label for w in [*at.selectbox, *at.multiselect, *at.radio]]
    assert labels == ["Window", "Columns", "Density"]


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
