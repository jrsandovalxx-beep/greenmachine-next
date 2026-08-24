"""SP-4 (D-119): the park orientation table's mechanical guarantees.

The bearings themselves were measured off retrieved ESRI imagery — the
provenance and its limits live in ``park_orientation``'s docstring. What the
suite pins here is what a local test can honestly pin: the table covers
exactly the open-air partition of ``PARK_VENUES``, the roofed eight stay out
by design, and every value is a Decimal degree reading a compass could
actually produce — so a transcription slip fails here rather than rotating a
wind read on the board.
"""

from __future__ import annotations

from decimal import Decimal

from greenmachine.inputs import PARK_ORIENTATION, PARK_VENUES
from greenmachine.inputs.contract import VenueType


def test_orientation_covers_exactly_the_open_air_partition() -> None:
    """One bearing per open-air venue, and no others: a missing row would
    silently mute that park's wind reads, and a stray row would claim an
    axis for a venue the reference does not know."""
    open_air = {venue.venue_id for venue in PARK_VENUES if venue.venue_type is VenueType.OPEN_AIR}
    assert len(open_air) == 22
    assert set(PARK_ORIENTATION) == open_air


def test_the_roofed_eight_stay_absent_by_design() -> None:
    """Wind state is never sourced for a roofed venue in v1 (D-073), so no
    roofed venue may carry an axis: finding one here would mean a wind read
    resolved against weather that never reached the field."""
    roofed = {venue.venue_id for venue in PARK_VENUES if venue.venue_type is not VenueType.OPEN_AIR}
    assert len(roofed) == 8
    assert roofed.isdisjoint(PARK_ORIENTATION)


def test_every_bearing_is_a_decimal_compass_reading() -> None:
    for venue_id, bearing in PARK_ORIENTATION.items():
        assert isinstance(bearing, Decimal), venue_id
        assert Decimal("0") <= bearing < Decimal("360"), venue_id
        # Whole degrees by design: finer digits would claim a precision the
        # measurement method does not hold (see the module docstring).
        assert bearing == bearing.to_integral_value(), venue_id
