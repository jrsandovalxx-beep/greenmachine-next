"""The GMF-002 grid: pure view logic over the ``InputSnapshot`` contract.

Everything here is ordinary importable code — pandas frames, ``Styler``
styles, selection consumption — with **no streamlit import**: the composition
root (`streamlit_app.py`) owns every widget, and this package owns everything
a widget hands off or receives. That line is D-061's testing boundary drawn
as an architecture line: AppTest asserts what the root handed to the element;
the functions here are proven by direct tests as ordinary code.
"""

from greenmachine.grid.selection import (
    DetailHandle,
    batter_for,
    detail_handle,
    selected_batter_id,
)
from greenmachine.grid.view import (
    ABSENCE_TEXT,
    BATTER_COLUMN,
    DENSITY_ROWS,
    METRIC_COLUMNS,
    FieldRow,
    MetricField,
    cell_text,
    display_state_frame,
    display_texts,
    frame_height,
    graded_styler,
    grid_frame,
    metric_fields,
    numeric_frame,
    row_batter_ids,
    state_frame,
    style_frame,
    style_frame_for,
    styled_text_frame,
    text_frame,
    visible_columns,
)

__all__ = [
    "ABSENCE_TEXT",
    "BATTER_COLUMN",
    "DENSITY_ROWS",
    "METRIC_COLUMNS",
    "DetailHandle",
    "FieldRow",
    "MetricField",
    "batter_for",
    "cell_text",
    "detail_handle",
    "display_state_frame",
    "display_texts",
    "frame_height",
    "graded_styler",
    "grid_frame",
    "metric_fields",
    "numeric_frame",
    "row_batter_ids",
    "selected_batter_id",
    "state_frame",
    "style_frame",
    "style_frame_for",
    "styled_text_frame",
    "text_frame",
    "visible_columns",
]
