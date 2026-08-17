"""Selection consumption for the grid (GMF-002, D-058).

Row selection (``on_select``) drives a detail **mechanism** — resolving the
component's positional selection to a batter and exposing a stable handle the
detail surface hangs off. The panel's *content* is GMF-003's scope; nothing
here renders.

Proven by direct tests as ordinary code (D-061): AppTest cannot synthesize a
row selection at the 1.37 floor, so this path's tests call these functions
with the payload shapes the component produces.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from greenmachine.inputs import BatterInputs, InputSnapshot


def selected_batter_id(rows: Sequence[int], ids: Sequence[str]) -> str | None:
    """The selected batter's id, or ``None`` for "no row selected".

    ``None`` here has exactly one meaning — the user has not selected a row —
    the single-meaning-``None`` shape the reviewer accepted for
    ``savant_venue_id``: nothing for the three-state trichotomy to
    distinguish. Everything irregular is an error, never a default: the
    component is configured single-row, so a multi-row payload is a contract
    breach and an out-of-range index is a positional-map bug — both raised,
    fail-closed.
    """
    if not rows:
        return None
    if len(rows) > 1:
        raise ValueError(
            f"single-row selection produced {len(rows)} rows; "
            "the component configuration and this consumer disagree"
        )
    row = rows[0]
    if not 0 <= row < len(ids):
        raise IndexError(f"selected row {row} is outside the {len(ids)}-row positional map")
    return ids[row]


@dataclass(frozen=True)
class DetailHandle:
    """The stable handle a detail surface hangs off — identity, not content."""

    batter_id: str
    name: str


def batter_for(snapshot: InputSnapshot, batter_id: str) -> BatterInputs:
    """Resolve a selected batter id to its inputs.

    Total over the snapshot's batters; an unknown id means the selection and
    the snapshot disagree — a programming error, raised rather than defaulted.
    """
    for batter in snapshot.batters:
        if batter.batter_id == batter_id:
            return batter
    raise LookupError(f"batter id {batter_id!r} is not in the rendered snapshot")


def detail_handle(snapshot: InputSnapshot, batter_id: str) -> DetailHandle:
    """Resolve a selected batter id to its handle — identity, not content."""
    batter = batter_for(snapshot, batter_id)
    return DetailHandle(batter_id=batter.batter_id, name=batter.name)
