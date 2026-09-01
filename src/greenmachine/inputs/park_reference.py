"""Park reference data: the thirty MLB venues with venue type (GMF-001 c3).

Provenance (D-055; provenance-pinned per §GMF-001 criterion 3): authored on
2026-08-05 for the 2026 season from each club's public
ballpark pages. Venue names and roof construction are public facts, not
provider datasets (D-052 does not bind them). Row count: 30. The partition is
22 open-air, 7 retractable-roof, 1 fixed-roof, pinned by test.

Volatile rows, recorded so drift is a data update rather than a surprise:
- The Athletics play at Sutter Health Park (open air) during the West
  Sacramento tenancy.
- Tropicana Field (fixed roof) is the Rays' venue with their scheduled 2026
  return after hurricane-damage repairs.
- Daikin Park (Houston, 2025 rename) and Rate Field (Chicago White Sox,
  2024 rename) carry their current names.
- UNIQLO Field at Dodger Stadium carries the March 2026 naming-rights name;
  the slug stays dodger-stadium and the join id is unchanged.

**Coordinates (§GMF-005), and their provenance stated honestly.** ``latitude``
and ``longitude`` are required because the NWS API is addressed only by
coordinate. Two things about them a reader is entitled to know:

- **Source.** They were recorded by the builder from general knowledge of where
  these ballparks are, not retrieved from any dataset: nothing fetched them, and
  no file was copied. Because **these particular values were not copied from any
  compilation**, no attribution is owed to a source they did not come from, and
  the origin is disclosed here instead. That is the narrow, load-bearing claim;
  this file makes no general assertion about how geographic data is licensed,
  which is not a question it is competent to settle.

  This is **weaker provenance than the pinned Savant snapshot beside them**,
  weaker than the ``savant_venue_id`` discipline in this same file — which
  deliberately binds against committed data rather than recall — and weaker than
  the standard this very docstring sets a few lines above, where the venue types
  name their source. It is disclosed rather than dressed up, and the value set
  can be replaced by a provenance-pinned export at any time without touching the
  contract.
- **Precision: three decimal places (~110 m), deliberately.** The requirement is
  landing in the right NWS gridpoint, and that grid is coarse — about 2.5 km — so
  110 m resolves it roughly twenty times over. A stadium footprint spans a
  couple of hundred metres, so finer digits would claim a surveyed point inside
  it that nobody measured. These identify the venue, not a seat in it.

Bounds, uniqueness and hemisphere are asserted by test, so a gross transcription
error fails the suite rather than reaching a forecast.

``venue_id`` is a stable slug and the primary key. ``savant_venue_id`` is
the join column to the pinned snapshot: its values are copied from the
committed export's own rows — the file and its sha256 digest are pinned by
data/SAVANT_PARK_FACTORS_PROVENANCE.md and by the snapshot test — never
from memory: the original authoring deliberately declined to assert MLBAM
ids from recall, and the join now binds against data. The Athletics carried
``None`` until D-166 moved the snapshot to a window covering Sutter Health
Park (opened 2025); their venue now joins on Savant id 2529 like every
other club, on the 2023-2026 four-season window derived at D-171.
"""

from __future__ import annotations

from decimal import Decimal

from greenmachine.inputs.contract import ParkVenue, VenueType

_OPEN = VenueType.OPEN_AIR
_RETRACTABLE = VenueType.RETRACTABLE_ROOF
_FIXED = VenueType.FIXED_ROOF

PARK_VENUES: tuple[ParkVenue, ...] = (
    ParkVenue(
        "chase-field",
        "Chase Field",
        "Arizona Diamondbacks",
        _RETRACTABLE,
        savant_venue_id=15,
        latitude=Decimal("33.445"),
        longitude=Decimal("-112.067"),
    ),
    ParkVenue(
        "sutter-health-park",
        "Sutter Health Park",
        "Athletics",
        _OPEN,
        savant_venue_id=2529,
        latitude=Decimal("38.580"),
        longitude=Decimal("-121.513"),
    ),
    ParkVenue(
        "truist-park",
        "Truist Park",
        "Atlanta Braves",
        _OPEN,
        savant_venue_id=4705,
        latitude=Decimal("33.891"),
        longitude=Decimal("-84.468"),
    ),
    ParkVenue(
        "camden-yards",
        "Oriole Park at Camden Yards",
        "Baltimore Orioles",
        _OPEN,
        savant_venue_id=2,
        latitude=Decimal("39.284"),
        longitude=Decimal("-76.622"),
    ),
    ParkVenue(
        "fenway-park",
        "Fenway Park",
        "Boston Red Sox",
        _OPEN,
        savant_venue_id=3,
        latitude=Decimal("42.347"),
        longitude=Decimal("-71.097"),
    ),
    ParkVenue(
        "wrigley-field",
        "Wrigley Field",
        "Chicago Cubs",
        _OPEN,
        savant_venue_id=17,
        latitude=Decimal("41.948"),
        longitude=Decimal("-87.655"),
    ),
    ParkVenue(
        "rate-field",
        "Rate Field",
        "Chicago White Sox",
        _OPEN,
        savant_venue_id=4,
        latitude=Decimal("41.830"),
        longitude=Decimal("-87.634"),
    ),
    ParkVenue(
        "great-american-ball-park",
        "Great American Ball Park",
        "Cincinnati Reds",
        _OPEN,
        savant_venue_id=2602,
        latitude=Decimal("39.097"),
        longitude=Decimal("-84.507"),
    ),
    ParkVenue(
        "progressive-field",
        "Progressive Field",
        "Cleveland Guardians",
        _OPEN,
        savant_venue_id=5,
        latitude=Decimal("41.496"),
        longitude=Decimal("-81.685"),
    ),
    ParkVenue(
        "coors-field",
        "Coors Field",
        "Colorado Rockies",
        _OPEN,
        savant_venue_id=19,
        latitude=Decimal("39.756"),
        longitude=Decimal("-104.994"),
    ),
    ParkVenue(
        "comerica-park",
        "Comerica Park",
        "Detroit Tigers",
        _OPEN,
        savant_venue_id=2394,
        latitude=Decimal("42.339"),
        longitude=Decimal("-83.049"),
    ),
    ParkVenue(
        "daikin-park",
        "Daikin Park",
        "Houston Astros",
        _RETRACTABLE,
        savant_venue_id=2392,
        latitude=Decimal("29.757"),
        longitude=Decimal("-95.355"),
    ),
    ParkVenue(
        "kauffman-stadium",
        "Kauffman Stadium",
        "Kansas City Royals",
        _OPEN,
        savant_venue_id=7,
        latitude=Decimal("39.051"),
        longitude=Decimal("-94.480"),
    ),
    ParkVenue(
        "angel-stadium",
        "Angel Stadium",
        "Los Angeles Angels",
        _OPEN,
        savant_venue_id=1,
        latitude=Decimal("33.800"),
        longitude=Decimal("-117.883"),
    ),
    ParkVenue(
        "dodger-stadium",
        "UNIQLO Field at Dodger Stadium",
        "Los Angeles Dodgers",
        _OPEN,
        savant_venue_id=22,
        latitude=Decimal("34.074"),
        longitude=Decimal("-118.240"),
    ),
    ParkVenue(
        "loandepot-park",
        "loanDepot park",
        "Miami Marlins",
        _RETRACTABLE,
        savant_venue_id=4169,
        latitude=Decimal("25.778"),
        longitude=Decimal("-80.220"),
    ),
    ParkVenue(
        "american-family-field",
        "American Family Field",
        "Milwaukee Brewers",
        _RETRACTABLE,
        savant_venue_id=32,
        latitude=Decimal("43.028"),
        longitude=Decimal("-87.971"),
    ),
    ParkVenue(
        "target-field",
        "Target Field",
        "Minnesota Twins",
        _OPEN,
        savant_venue_id=3312,
        latitude=Decimal("44.982"),
        longitude=Decimal("-93.278"),
    ),
    ParkVenue(
        "citi-field",
        "Citi Field",
        "New York Mets",
        _OPEN,
        savant_venue_id=3289,
        latitude=Decimal("40.757"),
        longitude=Decimal("-73.846"),
    ),
    ParkVenue(
        "yankee-stadium",
        "Yankee Stadium",
        "New York Yankees",
        _OPEN,
        savant_venue_id=3313,
        latitude=Decimal("40.830"),
        longitude=Decimal("-73.926"),
    ),
    ParkVenue(
        "citizens-bank-park",
        "Citizens Bank Park",
        "Philadelphia Phillies",
        _OPEN,
        savant_venue_id=2681,
        latitude=Decimal("39.906"),
        longitude=Decimal("-75.167"),
    ),
    ParkVenue(
        "pnc-park",
        "PNC Park",
        "Pittsburgh Pirates",
        _OPEN,
        savant_venue_id=31,
        latitude=Decimal("40.447"),
        longitude=Decimal("-80.006"),
    ),
    ParkVenue(
        "petco-park",
        "Petco Park",
        "San Diego Padres",
        _OPEN,
        savant_venue_id=2680,
        latitude=Decimal("32.707"),
        longitude=Decimal("-117.157"),
    ),
    ParkVenue(
        "t-mobile-park",
        "T-Mobile Park",
        "Seattle Mariners",
        _RETRACTABLE,
        savant_venue_id=680,
        latitude=Decimal("47.591"),
        longitude=Decimal("-122.332"),
    ),
    ParkVenue(
        "oracle-park",
        "Oracle Park",
        "San Francisco Giants",
        _OPEN,
        savant_venue_id=2395,
        latitude=Decimal("37.779"),
        longitude=Decimal("-122.389"),
    ),
    ParkVenue(
        "busch-stadium",
        "Busch Stadium",
        "St. Louis Cardinals",
        _OPEN,
        savant_venue_id=2889,
        latitude=Decimal("38.623"),
        longitude=Decimal("-90.193"),
    ),
    ParkVenue(
        "tropicana-field",
        "Tropicana Field",
        "Tampa Bay Rays",
        _FIXED,
        savant_venue_id=12,
        latitude=Decimal("27.768"),
        longitude=Decimal("-82.653"),
    ),
    ParkVenue(
        "globe-life-field",
        "Globe Life Field",
        "Texas Rangers",
        _RETRACTABLE,
        savant_venue_id=5325,
        latitude=Decimal("32.747"),
        longitude=Decimal("-97.085"),
    ),
    ParkVenue(
        "rogers-centre",
        "Rogers Centre",
        "Toronto Blue Jays",
        _RETRACTABLE,
        savant_venue_id=14,
        latitude=Decimal("43.641"),
        longitude=Decimal("-79.389"),
    ),
    ParkVenue(
        "nationals-park",
        "Nationals Park",
        "Washington Nationals",
        _OPEN,
        savant_venue_id=3309,
        latitude=Decimal("38.873"),
        longitude=Decimal("-77.007"),
    ),
)
