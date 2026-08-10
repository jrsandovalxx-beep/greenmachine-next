"""The GMF-002 grid: pure view logic over the ``InputSnapshot`` contract.

Everything here is ordinary importable code — pandas frames, ``Styler``
styles, selection consumption — with **no streamlit import**: the composition
root (`streamlit_app.py`) owns every widget, and this package owns everything
a widget hands off or receives. That line is D-061's testing boundary drawn
as an architecture line: AppTest asserts what the root handed to the element;
the functions here are proven by direct tests as ordinary code.
"""

from greenmachine.grid.selection import DetailHandle, detail_handle, selected_batter_id
from greenmachine.grid.view import (
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

__all__ = [
    "ABSENCE_TEXT",
    "BATTER_COLUMN",
    "DENSITY_ROWS",
    "METRIC_COLUMNS",
    "DetailHandle",
    "detail_handle",
    "frame_height",
    "graded_styler",
    "grid_frame",
    "row_batter_ids",
    "selected_batter_id",
    "state_frame",
    "style_lookup",
    "visible_columns",
]
