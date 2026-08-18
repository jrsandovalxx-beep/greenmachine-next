"""The GMF-004 weather seam (FEATURE_PHASE_PLAN §GMF-004 criterion 3).

One adapter interface, bound to a fixture in this ticket. The package holds
the seam alone: implementations live with their bindings — the fixture
adapter under ``greenmachine.fixtures``, and §GMF-005's live NWS adapter
wherever that ticket puts it — so importing the interface never drags a
provider in behind it.
"""

from greenmachine.weather.adapter import WeatherAdapter

__all__ = ["WeatherAdapter"]
