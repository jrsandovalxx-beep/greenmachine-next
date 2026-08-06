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

``venue_id`` is a stable slug. MLBAM numeric venue ids are deliberately not
asserted here: they are provider-published identifiers this ticket has no
pinned export for, and a wrong id silently mis-joins park factors. The Savant
snapshot (criterion 4) carries its own venue naming; the join is bound where
that file lands.
"""

from __future__ import annotations

from greenmachine.inputs.contract import ParkVenue, VenueType

_OPEN = VenueType.OPEN_AIR
_RETRACTABLE = VenueType.RETRACTABLE_ROOF
_FIXED = VenueType.FIXED_ROOF

PARK_VENUES: tuple[ParkVenue, ...] = (
    ParkVenue("chase-field", "Chase Field", "Arizona Diamondbacks", _RETRACTABLE),
    ParkVenue("sutter-health-park", "Sutter Health Park", "Athletics", _OPEN),
    ParkVenue("truist-park", "Truist Park", "Atlanta Braves", _OPEN),
    ParkVenue("camden-yards", "Oriole Park at Camden Yards", "Baltimore Orioles", _OPEN),
    ParkVenue("fenway-park", "Fenway Park", "Boston Red Sox", _OPEN),
    ParkVenue("wrigley-field", "Wrigley Field", "Chicago Cubs", _OPEN),
    ParkVenue("rate-field", "Rate Field", "Chicago White Sox", _OPEN),
    ParkVenue("great-american-ball-park", "Great American Ball Park", "Cincinnati Reds", _OPEN),
    ParkVenue("progressive-field", "Progressive Field", "Cleveland Guardians", _OPEN),
    ParkVenue("coors-field", "Coors Field", "Colorado Rockies", _OPEN),
    ParkVenue("comerica-park", "Comerica Park", "Detroit Tigers", _OPEN),
    ParkVenue("daikin-park", "Daikin Park", "Houston Astros", _RETRACTABLE),
    ParkVenue("kauffman-stadium", "Kauffman Stadium", "Kansas City Royals", _OPEN),
    ParkVenue("angel-stadium", "Angel Stadium", "Los Angeles Angels", _OPEN),
    ParkVenue("dodger-stadium", "Dodger Stadium", "Los Angeles Dodgers", _OPEN),
    ParkVenue("loandepot-park", "loanDepot park", "Miami Marlins", _RETRACTABLE),
    ParkVenue("american-family-field", "American Family Field", "Milwaukee Brewers", _RETRACTABLE),
    ParkVenue("target-field", "Target Field", "Minnesota Twins", _OPEN),
    ParkVenue("citi-field", "Citi Field", "New York Mets", _OPEN),
    ParkVenue("yankee-stadium", "Yankee Stadium", "New York Yankees", _OPEN),
    ParkVenue("citizens-bank-park", "Citizens Bank Park", "Philadelphia Phillies", _OPEN),
    ParkVenue("pnc-park", "PNC Park", "Pittsburgh Pirates", _OPEN),
    ParkVenue("petco-park", "Petco Park", "San Diego Padres", _OPEN),
    ParkVenue("t-mobile-park", "T-Mobile Park", "Seattle Mariners", _RETRACTABLE),
    ParkVenue("oracle-park", "Oracle Park", "San Francisco Giants", _OPEN),
    ParkVenue("busch-stadium", "Busch Stadium", "St. Louis Cardinals", _OPEN),
    ParkVenue("tropicana-field", "Tropicana Field", "Tampa Bay Rays", _FIXED),
    ParkVenue("globe-life-field", "Globe Life Field", "Texas Rangers", _RETRACTABLE),
    ParkVenue("rogers-centre", "Rogers Centre", "Toronto Blue Jays", _RETRACTABLE),
    ParkVenue("nationals-park", "Nationals Park", "Washington Nationals", _OPEN),
)
