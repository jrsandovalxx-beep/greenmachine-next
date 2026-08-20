"""§GMF-005's contract addition: every venue is addressable, and plausibly so.

Coordinates were recorded by the builder rather than bound against a committed
export — weaker provenance than the pinned Savant snapshot beside them, and
disclosed as such in ``park_reference``'s own docstring. These tests are the
mechanical compensation: a gross transcription error fails the suite here rather
than quietly asking NWS about the wrong place.

They deliberately do **not** claim the values are correct. No test in a fully
local suite can establish that; what they establish is that nothing is missing,
duplicated, out of range, on the wrong side of the planet, or precise beyond
what anyone measured.
"""

from __future__ import annotations

from decimal import Decimal

from greenmachine.inputs import PARK_VENUES

# The continental envelope of MLB: San Diego to Toronto, Miami to Seattle, with
# margin. Wide enough not to encode a false precision, tight enough that a
# transposed sign or swapped pair cannot pass.
MIN_LATITUDE, MAX_LATITUDE = Decimal("24"), Decimal("50")
MIN_LONGITUDE, MAX_LONGITUDE = Decimal("-125"), Decimal("-66")

MAX_DECIMAL_PLACES = 3


def test_every_venue_is_addressable() -> None:
    """The point of making the fields required: an unaddressable venue cannot
    be constructed, so this can only fail if the reference data shrinks."""
    assert len(PARK_VENUES) == 30
    for venue in PARK_VENUES:
        assert isinstance(venue.latitude, Decimal)
        assert isinstance(venue.longitude, Decimal)


def test_every_venue_sits_inside_the_north_american_envelope() -> None:
    for venue in PARK_VENUES:
        assert MIN_LATITUDE <= venue.latitude <= MAX_LATITUDE, venue.venue_id
        assert MIN_LONGITUDE <= venue.longitude <= MAX_LONGITUDE, venue.venue_id


def test_no_two_venues_share_a_location() -> None:
    """Two ballparks at one point would mean a copied row, and would send one
    venue's forecast to the other's gridpoint."""
    located = {(venue.latitude, venue.longitude) for venue in PARK_VENUES}
    assert len(located) == len(PARK_VENUES)


def test_rogers_centre_is_located_in_toronto() -> None:
    """The one venue whose location is load-bearing beyond addressing.

    D-055 names it as the venue NWS does not cover, and §GMF-005 submission 2
    uses that non-coverage as its *unavailable* demonstration — produced by the
    source answering honestly rather than by a hardcoded country check, which
    the product deliberately does not contain. If these coordinates drifted into
    the United States the demonstration would silently become a real forecast.

    An earlier version of this test asserted Rogers Centre was the only venue
    north of 43.5°N. That was false about the world, not about the data: Target
    Field and T-Mobile Park both sit further north than Toronto. Latitude does
    not identify a country, so the check now bounds the actual city.
    """
    rogers = next(venue for venue in PARK_VENUES if venue.venue_id == "rogers-centre")
    assert Decimal("43.5") <= rogers.latitude <= Decimal("43.8")
    assert Decimal("-79.6") <= rogers.longitude <= Decimal("-79.2")


def test_precision_is_bounded_at_the_stated_three_places() -> None:
    """Three decimals is ~110 m against an NWS grid of ~2.5 km. More digits
    would claim a surveyed point nobody measured; the docstring states this and
    the data has to match the claim."""
    for venue in PARK_VENUES:
        for value in (venue.latitude, venue.longitude):
            assert -value.as_tuple().exponent <= MAX_DECIMAL_PLACES, venue.venue_id


def test_the_venue_the_savant_export_skips_is_still_addressable() -> None:
    """The Athletics have no park-factor row (provenance finding 1) and that gap
    is represented, not filled — but they still play somewhere, and the weather
    seam must be able to ask about it."""
    athletics = next(venue for venue in PARK_VENUES if venue.savant_venue_id is None)
    assert athletics.venue_id == "sutter-health-park"
    assert MIN_LATITUDE <= athletics.latitude <= MAX_LATITUDE
