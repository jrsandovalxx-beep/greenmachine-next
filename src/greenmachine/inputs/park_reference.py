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

``venue_id`` is a stable slug and the primary key. ``savant_venue_id`` is
the join column to the pinned snapshot: its values are copied from the
committed export's own rows — the file and its sha256 digest are pinned by
data/SAVANT_PARK_FACTORS_PROVENANCE.md and by the snapshot test — never
from memory: the original authoring deliberately declined to assert MLBAM
ids from recall, and the join now binds against data. The Athletics carry
``None``: the snapshot has no row for their venue (provenance finding 1 —
the reason is *not yet observed*: the 2024-2026 rolling window has not
accumulated Sutter Health Park history), and the gap is represented, never
filled.
"""

from __future__ import annotations

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
    ),
    ParkVenue(
        "sutter-health-park",
        "Sutter Health Park",
        "Athletics",
        _OPEN,
        savant_venue_id=None,
    ),
    ParkVenue(
        "truist-park",
        "Truist Park",
        "Atlanta Braves",
        _OPEN,
        savant_venue_id=4705,
    ),
    ParkVenue(
        "camden-yards",
        "Oriole Park at Camden Yards",
        "Baltimore Orioles",
        _OPEN,
        savant_venue_id=2,
    ),
    ParkVenue(
        "fenway-park",
        "Fenway Park",
        "Boston Red Sox",
        _OPEN,
        savant_venue_id=3,
    ),
    ParkVenue(
        "wrigley-field",
        "Wrigley Field",
        "Chicago Cubs",
        _OPEN,
        savant_venue_id=17,
    ),
    ParkVenue(
        "rate-field",
        "Rate Field",
        "Chicago White Sox",
        _OPEN,
        savant_venue_id=4,
    ),
    ParkVenue(
        "great-american-ball-park",
        "Great American Ball Park",
        "Cincinnati Reds",
        _OPEN,
        savant_venue_id=2602,
    ),
    ParkVenue(
        "progressive-field",
        "Progressive Field",
        "Cleveland Guardians",
        _OPEN,
        savant_venue_id=5,
    ),
    ParkVenue(
        "coors-field",
        "Coors Field",
        "Colorado Rockies",
        _OPEN,
        savant_venue_id=19,
    ),
    ParkVenue(
        "comerica-park",
        "Comerica Park",
        "Detroit Tigers",
        _OPEN,
        savant_venue_id=2394,
    ),
    ParkVenue(
        "daikin-park",
        "Daikin Park",
        "Houston Astros",
        _RETRACTABLE,
        savant_venue_id=2392,
    ),
    ParkVenue(
        "kauffman-stadium",
        "Kauffman Stadium",
        "Kansas City Royals",
        _OPEN,
        savant_venue_id=7,
    ),
    ParkVenue(
        "angel-stadium",
        "Angel Stadium",
        "Los Angeles Angels",
        _OPEN,
        savant_venue_id=1,
    ),
    ParkVenue(
        "dodger-stadium",
        "UNIQLO Field at Dodger Stadium",
        "Los Angeles Dodgers",
        _OPEN,
        savant_venue_id=22,
    ),
    ParkVenue(
        "loandepot-park",
        "loanDepot park",
        "Miami Marlins",
        _RETRACTABLE,
        savant_venue_id=4169,
    ),
    ParkVenue(
        "american-family-field",
        "American Family Field",
        "Milwaukee Brewers",
        _RETRACTABLE,
        savant_venue_id=32,
    ),
    ParkVenue(
        "target-field",
        "Target Field",
        "Minnesota Twins",
        _OPEN,
        savant_venue_id=3312,
    ),
    ParkVenue(
        "citi-field",
        "Citi Field",
        "New York Mets",
        _OPEN,
        savant_venue_id=3289,
    ),
    ParkVenue(
        "yankee-stadium",
        "Yankee Stadium",
        "New York Yankees",
        _OPEN,
        savant_venue_id=3313,
    ),
    ParkVenue(
        "citizens-bank-park",
        "Citizens Bank Park",
        "Philadelphia Phillies",
        _OPEN,
        savant_venue_id=2681,
    ),
    ParkVenue(
        "pnc-park",
        "PNC Park",
        "Pittsburgh Pirates",
        _OPEN,
        savant_venue_id=31,
    ),
    ParkVenue(
        "petco-park",
        "Petco Park",
        "San Diego Padres",
        _OPEN,
        savant_venue_id=2680,
    ),
    ParkVenue(
        "t-mobile-park",
        "T-Mobile Park",
        "Seattle Mariners",
        _RETRACTABLE,
        savant_venue_id=680,
    ),
    ParkVenue(
        "oracle-park",
        "Oracle Park",
        "San Francisco Giants",
        _OPEN,
        savant_venue_id=2395,
    ),
    ParkVenue(
        "busch-stadium",
        "Busch Stadium",
        "St. Louis Cardinals",
        _OPEN,
        savant_venue_id=2889,
    ),
    ParkVenue(
        "tropicana-field",
        "Tropicana Field",
        "Tampa Bay Rays",
        _FIXED,
        savant_venue_id=12,
    ),
    ParkVenue(
        "globe-life-field",
        "Globe Life Field",
        "Texas Rangers",
        _RETRACTABLE,
        savant_venue_id=5325,
    ),
    ParkVenue(
        "rogers-centre",
        "Rogers Centre",
        "Toronto Blue Jays",
        _RETRACTABLE,
        savant_venue_id=14,
    ),
    ParkVenue(
        "nationals-park",
        "Nationals Park",
        "Washington Nationals",
        _OPEN,
        savant_venue_id=3309,
    ),
)
