"""Live data acquisition for the MLB research dashboard (D-069, D-070).

This package is the only place in ``src/`` besides ``weather/`` allowed to
open a network connection. It speaks to exactly two hosts —
``statsapi.mlb.com`` and ``baseballsavant.mlb.com`` — through
:class:`~greenmachine.live.transport.UrllibTransport`, which pins the
allowlist and re-validates every redirect target.

Boundary rules (all enforced by architecture tests):

- No clock reads: dates and instants arrive as parameters.
- No caching here: the composition root owns caches (D-070).
- No broad exception catches: transport and payload failures are typed and
  surface as :class:`~greenmachine.live.mlb_api.FetchFailure`.
- No thresholds: boards return raw observed values; the grading config owns
  every bucket boundary.
"""
