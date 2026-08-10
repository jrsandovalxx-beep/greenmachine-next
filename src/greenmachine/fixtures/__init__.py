"""App-side fixtures: snapshots the deployed app renders (GMF-002).

Production surfaces cannot import from ``tests/`` — the synthetic builders
under ``tests/unit/inputs/`` are test code — so the app's fixture snapshots
are built here, under the same OQ-4 discipline: every number is deliberately
non-baseball, so the public page cannot be mistaken for real data and no
provider-data question arises (D-051/D-052 untouched).
"""

from greenmachine.fixtures.grid_demo import grid_demo_snapshot

__all__ = ["grid_demo_snapshot"]
