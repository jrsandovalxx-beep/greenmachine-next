"""§GMF-003 criterion 6: the metrics screen, asserted at the element.

D-061's boundary applies unchanged — AppTest proves what the page handed the
component (data, display values, column configuration) and the screen's policy
is proven as ordinary code in ``tests/unit/splits``. Nothing here claims a
gradient is legible.

The screen is reachable without a row selection **by design**: AppTest cannot
synthesize one at the 1.37 floor, and criterion 6 asks for AppTest with no
deployed submission to fall back on, so a surface hidden behind an
unsynthesizable click could not be verified as the criterion requires.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pytest
from streamlit.testing.v1 import AppTest

from greenmachine.splits import METRIC_COLUMNS, PITCH_TYPE_COLUMN

_APP_PATH = Path(__file__).resolve().parents[2] / "streamlit_app.py"
_TIMEOUT = 15


def _run_app() -> AppTest:
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _splits_elements(at: AppTest) -> list[Any]:
    """Every pitch-type grid on the page, by this screen's own column signature.

    Previously "the dataframe that is not the keyed batter grid", which was
    exact while the page carried two tables and stopped being exact the moment
    §GMF-004 added the parks table — a non-selectable dataframe carries no
    proto id, so it matched the not-the-grid filter too. Identifying the
    element by the column only this screen has keeps each assertion pointed at
    the surface it was written for, however many tables the page grows.
    """
    return [element for element in at.dataframe if PITCH_TYPE_COLUMN in list(element.value.columns)]


def _splits_element(at: AppTest) -> Any:
    """The pitch-type grid: exactly one when the screen is showing a batter."""
    others = _splits_elements(at)
    assert len(others) == 1, f"expected one pitch-type grid, found {len(others)}"
    return others[0]


def _arrow_surface(proto: Any) -> Any:
    """The Arrow-carrying message, across both proto schemas — resolved by
    DESCRIPTOR, exactly as the GMF-002 suite's accessor does and for the same
    reason: at the 1.37 floor the field is absent from the SCHEMA, so
    ``HasField`` raises ValueError instead of returning False. This module's
    first version used ``HasField`` and the floor run caught it — the
    probe-binds-code rule doing precisely what it exists to do."""
    field_names = {f.name for f in proto.DESCRIPTOR.fields}
    return proto.arrow_data if "arrow_data" in field_names else proto


def _read(payload: bytes) -> pd.DataFrame:
    return pa.ipc.open_stream(io.BytesIO(payload)).read_pandas()


def _select_batter(at: AppTest, name: str) -> AppTest:
    at.selectbox(key="splits_batter").set_value(name).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _run_selected(name: str = "Batter Alpha") -> AppTest:
    """The screen after a user-composed choice — which is the only way any
    split data renders: the initial state selects nobody (D-015/D-017)."""
    return _select_batter(_run_app(), name)


def test_the_screen_is_reachable_without_a_grid_row_selection() -> None:
    """Criterion 6's reachability: the ordinary Batter control opens the
    surface — no grid row selection (which AppTest cannot synthesize at the
    1.37 floor) is involved anywhere on this path."""
    at = _run_selected()
    assert _splits_element(at) is not None


def test_the_initial_state_selects_nobody():  # D-015/D-017
    """Before the user acts, the product has chosen no hitter. index=0 was an
    automated selection of one batter — neutral ordering does not cure it,
    because "the first neutral item" is still a product-composed choice. The
    control starts empty and an invitation renders in place of the surface."""
    at = _run_app()
    assert at.selectbox(key="splits_batter").value is None
    captions = " | ".join(c.value for c in at.caption)
    assert "Choose a batter to read their pitch-type splits." in captions
    assert "Nothing is selected for you." in captions
    # No split surface exists yet: no second dataframe, no window statement.
    assert not _splits_elements(at)
    body = " | ".join(m.value for m in at.markdown)
    assert "**Window:** SEASON_TO_DATE" not in body


def test_selecting_a_batter_replaces_the_invitation() -> None:
    at = _run_selected()
    captions = " | ".join(c.value for c in at.caption)
    assert "Nothing is selected for you." not in captions
    assert _splits_element(at) is not None


def test_the_window_is_named_on_the_screen() -> None:
    """Criterion 2 at the page: the window is stated, not implied."""
    at = _run_selected()
    body = " | ".join(m.value for m in at.markdown)
    assert "**Window:** SEASON_TO_DATE" in body
    assert "current season" in body


def test_no_window_control_exists_on_the_metrics_screen() -> None:
    """The window is fixed for this screen. The only window selector on the
    page is the batter grid's, which belongs to that screen."""
    at = _run_app()
    assert [w.label for w in at.selectbox if w.label == "Window"] == ["Window"]
    assert at.selectbox(key="splits_batter").label == "Batter"


def test_the_threshold_is_stated_on_the_screen() -> None:
    """Criterion 3: the threshold is a number the reader can see."""
    at = _run_selected()
    captions = " | ".join(c.value for c in at.caption)
    assert "at or above 15% usage share" in captions


def test_the_element_carries_only_qualifying_pitch_types() -> None:
    at = _run_selected()
    frame = _splits_element(at).value
    assert list(frame[PITCH_TYPE_COLUMN]) == ["CH", "FF", "SL"]


def test_the_element_columns_are_the_seven_metrics_in_canonical_order() -> None:
    at = _run_selected()
    proto = _splits_element(at).proto
    assert list(proto.column_order) == [PITCH_TYPE_COLUMN, *METRIC_COLUMNS]


def test_the_element_metric_data_is_numeric_so_header_sort_is_numeric() -> None:
    """The same discipline the batter grid proved: raw values ride the data and
    the rendered text rides the Styler, so sorting is numeric."""
    at = _run_selected()
    surface = _arrow_surface(_splits_element(at).proto)
    data = _read(surface.data)
    for column in METRIC_COLUMNS:
        assert data[column].dtype.kind == "f"


def test_the_element_display_values_name_each_denominator() -> None:
    """Criterion 4 at the element: every rendered cell carries its own
    denominator, and the two near-identical ones stay apart."""
    at = _run_selected()
    surface = _arrow_surface(_splits_element(at).proto)
    rendered = _read(surface.styler.display_values)
    flat = " ".join(str(v) for v in rendered.to_numpy().ravel())
    assert "pitches, all types" in flat  # Usage %
    assert "pitches, this type" in flat  # SwStr%
    assert "swings" in flat  # Whiff%
    assert "BBE" in flat  # barrel rate / exit velocity
    assert "AB" in flat  # ISO
    assert "PA" in flat  # xwOBA


def test_the_element_renders_an_absent_metric_as_its_reason() -> None:
    """SL qualifies with an unavailable xwOBA: the row stays, the cell says why."""
    at = _run_selected()
    surface = _arrow_surface(_splits_element(at).proto)
    rendered = _read(surface.styler.display_values)
    flat = " ".join(str(v) for v in rendered.to_numpy().ravel())
    assert "source unavailable" in flat


def test_the_suppressed_types_are_acknowledged_by_name_on_the_page() -> None:
    at = _run_selected()
    body = " | ".join(m.value for m in at.markdown)
    assert "CU" in body and "SI" in body  # measured and below the threshold
    assert "KC" in body and "FS" in body  # usage never observed
    assert "unevaluable" in body


def test_the_page_states_each_metrics_denominator_and_provenance() -> None:
    at = _run_selected()
    body = " | ".join(m.value for m in at.markdown)
    for column in METRIC_COLUMNS:
        assert f"{column} —" in body
    assert "from source for every shown pitch type, not computed" in body
    # Nothing in the fixture derives, so no column may claim a mixed state.
    assert "MIXED" not in body


@pytest.mark.parametrize(
    ("batter", "expected"),
    [
        ("Batter Charlie", "not yet observed"),
        ("Batter Delta", "source unavailable"),
        ("Batter Echo", "not applicable"),
    ],
)
def test_an_absent_split_set_reports_its_own_reason(batter: str, expected: str) -> None:
    """The set-level absence, distinct per reason — never an empty table."""
    at = _select_batter(_run_app(), batter)
    info = " | ".join(i.value for i in at.info)
    assert expected in info
    assert "No pitch-type splits to show" in info
    # No table at all, rather than an empty one that would read as "no types".
    assert not _splits_elements(at)


def test_a_batter_who_faced_no_pitches_reads_as_an_observation() -> None:
    """Present and empty: the source answered. Not the same as absent, and the
    page says which."""
    at = _select_batter(_run_app(), "Batter Bravo")
    info = " | ".join(i.value for i in at.info)
    assert "faced no tracked pitches" in info
    assert "this is a measurement, not a missing one" in info


def test_the_batter_control_changes_the_rendered_screen() -> None:
    """The chooser is real: switching batters changes what the element shows."""
    at = _run_selected()
    before = list(_splits_element(at).value[PITCH_TYPE_COLUMN])
    at = _select_batter(at, "Batter Charlie")
    remaining = _splits_elements(at)
    assert before == ["CH", "FF", "SL"]
    assert not remaining  # an absent set renders no table at all


def test_the_page_states_absent_cells_in_words_beneath_the_grid() -> None:
    """The canvas renders a null-data cell as the component's own ``None``
    (observed on the local render), so the reason is also stated as text."""
    at = _run_selected()
    body = " | ".join(m.value for m in at.markdown)
    assert "**Absent metrics on the rows above, in words**" in body
    assert "SL — xwOBA (source unavailable" in body
