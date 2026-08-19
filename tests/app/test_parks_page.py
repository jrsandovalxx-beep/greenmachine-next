"""GMF-004 criterion 6: the parks element, asserted at the element boundary.

D-061's boundary kept as GMF-002 and GMF-003 kept it — AppTest proves what the
composition root handed to the element; the view functions are proven as
ordinary code in `tests/unit/parks/`. The element is selected by its own key,
never by position: the page now carries three dataframes, and a positional
index would silently start asserting this ticket's criteria against another
screen's element.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from greenmachine.fixtures import FixtureWeatherAdapter
from greenmachine.parks import (
    ALL_COLUMNS,
    FORECAST_COLUMN,
    LHB_FACTOR_COLUMN,
    RHB_FACTOR_COLUMN,
    ROOF_COLUMN,
    VENUE_COLUMN,
    VENUE_TYPE_COLUMN,
)
from greenmachine.weather.nws import NwsWeatherAdapter

_APP_PATH = Path(__file__).resolve().parents[2] / "streamlit_app.py"

_TIMEOUT = 30


def _run_app() -> AppTest:
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _parks_element(at: AppTest) -> Any:
    """The parks table, selected by its own column signature.

    Not by position, and not by proto id: only a *selectable* dataframe is a
    widget and carries an id, and this table deliberately is not one — nothing
    on this screen consumes a row selection, and an affordance that leads
    nowhere is worse than none. The venue column is the surface's own identity
    and cannot be confused with the batter grid's or the pitch-type grid's.
    """
    elements = [element for element in at.dataframe if VENUE_COLUMN in list(element.value.columns)]
    assert len(elements) == 1, f"expected one parks table, found {len(elements)}"
    return elements[0]


def test_the_page_renders_the_parks_table() -> None:
    element = _parks_element(_run_app())
    frame = element.value
    assert len(frame) == 30  # every venue in the reference data
    assert list(frame.columns) == [VENUE_COLUMN, *ALL_COLUMNS]


def test_the_element_receives_all_columns_in_the_configured_order() -> None:
    """Column visibility is the user's control; what the root hands over is the
    full ordered set with venue type immediately before the factors."""
    order = list(_parks_element(_run_app()).proto.column_order)
    assert order == [VENUE_COLUMN, *ALL_COLUMNS]
    assert order.index(VENUE_TYPE_COLUMN) < order.index(LHB_FACTOR_COLUMN)
    assert order.index(LHB_FACTOR_COLUMN) < order.index(RHB_FACTOR_COLUMN)


def test_rows_arrive_in_neutral_venue_order() -> None:
    names = list(_parks_element(_run_app()).value[VENUE_COLUMN])
    assert names == sorted(names)
    assert names[0] != "Coors Field"  # not factor-ordered, which would lead here


def test_factor_columns_reach_the_element_as_numbers() -> None:
    frame = _parks_element(_run_app()).value
    for column in (LHB_FACTOR_COLUMN, RHB_FACTOR_COLUMN):
        assert str(frame[column].dtype) == "float64"


def test_condition_columns_reach_the_element_as_words() -> None:
    """The roof and forecast text is in the data the element received, so it
    cannot be dropped the way a null cell's display value is."""
    frame = _parks_element(_run_app()).value
    for column in (ROOF_COLUMN, FORECAST_COLUMN):
        values = [str(value) for value in frame[column]]
        assert all(value.strip() for value in values)


def test_no_forecast_values_ride_a_closed_or_undetermined_roof() -> None:
    """Criterion 4 at the element: the suppressed rows carry the reason, and
    no temperature or wind figure appears in them."""
    frame = _parks_element(_run_app()).value
    suppressed = [
        str(row[FORECAST_COLUMN])
        for _index, row in frame.iterrows()
        if "not shown" in str(row[FORECAST_COLUMN])
    ]
    assert suppressed, "no venue exercises the suppressed path on the composed page"
    for text in suppressed:
        assert "°F" not in text
        assert "mph" not in text


def test_the_three_roof_renderings_all_appear_on_the_page() -> None:
    roofs = {str(value) for value in _parks_element(_run_app()).value[ROOF_COLUMN]}
    assert any("open air" in text for text in roofs)
    assert any("fixed" in text for text in roofs)
    assert any("retractable — open" in text for text in roofs)
    assert any("retractable — closed" in text for text in roofs)
    assert any("state unknown" in text for text in roofs)


def test_the_page_states_the_window_and_the_export_date() -> None:
    """The provenance record's standing requirement: a screen rendering these
    factors says which rolling window they describe — and this page also says
    how old the export is, so it cannot imply fresher data than it holds."""
    captions = " ".join(element.value for element in _run_app().caption)
    assert "2024-2026" in captions
    assert "rolling" in captions
    assert "2026-08-06" in captions


def test_the_page_names_the_fixture_binding_and_where_a_live_source_arrives() -> None:
    captions = " ".join(element.value for element in _run_app().caption)
    assert "fixture" in captions.lower()
    assert "GMF-005" in captions


def test_absent_factors_are_stated_in_words_somewhere_on_the_page() -> None:
    """The authorized additive remedy: the Athletics' gap is readable, not left
    to a cell the component renders as its own null."""
    at = _run_app()
    markdown = " ".join(element.value for element in at.markdown)
    assert "Sutter Health Park" in markdown
    assert "not yet observed" in markdown


# --- §GMF-005: the binding, and the captions that must stay true ------------


def test_a_local_render_binds_the_fixture_and_never_the_network() -> None:
    """The ratified discriminator, asserted at the page.

    Every test in this suite runs local, and GM-008 would fail any of them that
    reached a socket — but a passing suite is not the claim. The claim is that
    the page *chooses* the fixture locally, which is what keeps the local-render
    evidence route alive for this ticket and the ones after it.
    """
    captions = " ".join(element.value for element in _run_app().caption)
    assert "fixture-bound" in captions
    assert "local" in captions
    assert "api.weather.gov" not in captions


def test_the_page_names_which_weather_binding_is_live_for_this_environment() -> None:
    """Honesty in both directions: the local page says local, so a reader is
    never left inferring which of the two states they are looking at."""
    captions = " ".join(element.value for element in _run_app().caption)
    assert "local environment" in captions


def test_the_page_level_caption_names_every_section_it_renders() -> None:
    """The GMF-004 V1 defect class, pre-empted: a global claim that outlives
    the ticket it described is exactly what the render caught last time."""
    captions = " ".join(element.value for element in _run_app().caption)
    assert "§GMF-005" in captions
    # The claim that went false when weather gained a source must be gone.
    assert "conditions are fixture-bound until" not in captions


def test_the_page_names_when_its_forecasts_were_retrieved() -> None:
    """A freshness bound stated only in code says nothing to the reader; the
    ruling asks for the retrieval time on the surface, and the fixture's
    injected clock makes it a fixed, honest value rather than a live read."""
    captions = " ".join(element.value for element in _run_app().caption)
    assert "Forecasts retrieved" in captions
    assert "2026-01-01T12:00:00+00:00" in captions


def test_roof_is_still_described_as_fixture_bound() -> None:
    """Weather gained a source in this ticket and roof did not. A reader who
    saw one go live would otherwise assume the other did too."""
    captions = " ".join(element.value for element in _run_app().caption)
    assert "roof" in captions.lower()
    assert "fixture" in captions.lower()


def test_the_discriminator_chooses_the_live_adapter_only_off_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both directions of ruling B, proven on the function rather than the page.

    Deliberately never calls ``forecast_for``: binding the live adapter is
    correct, using it inside this suite is not. GM-008 raises a ``RuntimeError``
    from the socket layer, which is not a ``TransportError`` and would not be
    caught — the adapter's failure mapping covers a network that answers badly,
    not a suite that has forbidden networking outright. So this asserts the
    choice and stops there.
    """
    import streamlit_app

    monkeypatch.setenv("GM_ENVIRONMENT", "staging")
    adapter, live = streamlit_app.weather_binding()
    assert live is True
    assert isinstance(adapter, NwsWeatherAdapter)

    monkeypatch.setenv("GM_ENVIRONMENT", "local")
    adapter, live = streamlit_app.weather_binding()
    assert live is False
    assert isinstance(adapter, FixtureWeatherAdapter)
