"""GMF-002 direct tests: selection consumption as ordinary code (D-061/D-058).

AppTest cannot synthesize a row selection at the 1.37 floor, so this path is
proven here with the payload shapes the component produces: an empty list, a
single positional row, and the irregular shapes that must fail closed.
"""

from __future__ import annotations

import pytest

from greenmachine.fixtures import grid_demo_snapshot
from greenmachine.grid import DetailHandle, detail_handle, row_batter_ids, selected_batter_id

SNAPSHOT = grid_demo_snapshot()
IDS = row_batter_ids(SNAPSHOT)


def test_no_selection_means_none_and_none_means_only_that() -> None:
    """The single-meaning ``None`` (the savant_venue_id shape): the user has
    not selected a row — nothing for the trichotomy to distinguish."""
    assert selected_batter_id((), IDS) is None


@pytest.mark.parametrize("row", range(5))
def test_a_single_selected_row_resolves_through_the_positional_map(row: int) -> None:
    assert selected_batter_id((row,), IDS) == IDS[row]


def test_a_multi_row_payload_fails_closed() -> None:
    """The component is configured single-row; a multi-row payload means the
    configuration and the consumer disagree — an error, never a default."""
    with pytest.raises(ValueError, match="single-row"):
        selected_batter_id((0, 1), IDS)


@pytest.mark.parametrize("row", [-1, 5, 99])
def test_an_out_of_range_row_fails_closed(row: int) -> None:
    with pytest.raises(IndexError, match="positional map"):
        selected_batter_id((row,), IDS)


def test_the_detail_handle_resolves_identity_not_content() -> None:
    """D-058: selection drives a detail mechanism; the handle carries
    identity only — the panel's content is GMF-003's scope."""
    handle = detail_handle(SNAPSHOT, "grid-demo-2")
    assert handle == DetailHandle(batter_id="grid-demo-2", name="Batter Bravo")


def test_an_unknown_batter_id_fails_closed() -> None:
    with pytest.raises(LookupError, match="not in the rendered snapshot"):
        detail_handle(SNAPSHOT, "no-such-batter")
