"""The GMF-004 weather seam (FEATURE_PHASE_PLAN §GMF-004 criterion 3).

One adapter interface. Implementations live beside their bindings — the
fixture adapter under ``greenmachine.fixtures``, and §GMF-005's live NWS
adapter in ``greenmachine.weather.nws`` with its network edge in
``greenmachine.weather.transport``.

This module exports the interface and nothing else, so importing the seam
still never drags a provider in behind it: a caller who wants the live
adapter has to name it, and the fixture package imports only this interface.
"""

from greenmachine.weather.adapter import WeatherAdapter

__all__ = ["WeatherAdapter"]
