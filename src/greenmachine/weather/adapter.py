"""The §GMF-004 weather seam: one adapter interface, and nothing else.

Criterion 3 asks for **one** adapter interface, bound here to a fixture. This
module is deliberately the whole of that seam — a protocol and its docstring.
No implementation lives here, so nothing in the seam can quietly acquire a
provider, a URL or a credential (D-051/D-056: the project has no secrets, and
this ticket does not introduce the first one). §GMF-005 binds a live NWS
implementation behind this same interface later; the screen it feeds does not
change when it does, which is the point of putting the seam in before the
source.

**Unavailability is a return value, not an exception.** ``forecast_for``
answers with a ``SnapshotField``, so a source that does not answer produces an
ordinary absence carrying its reason — the contract's three-way absence
(§7) reaching the screen through the same channel as a present forecast.
Criterion 3's "renders correctly with the adapter returning *unavailable*" is
therefore ordinary flow rather than error handling, and no caller needs a
``try`` to stay correct.
"""

from __future__ import annotations

from typing import Protocol

from greenmachine.inputs import ParkVenue, SnapshotField, SourceRecord, WeatherForecast


class WeatherAdapter(Protocol):
    """One venue in, one observed forecast field out.

    An implementation names its own source in the field it returns
    (``SnapshotField.source_id``), so a snapshot built from several adapters
    keeps each observation's provenance separable. The ``source`` record is
    the same naming, hoisted to the seam: a snapshot builder must *declare*
    every source its fields name (the contract rejects an undeclared id), so
    the record cannot live only inside individual fields.
    """

    source: SourceRecord

    def forecast_for(self, venue: ParkVenue) -> SnapshotField[WeatherForecast]:
        """The forecast observed for ``venue`` — present, or absent with a reason."""
        ...
