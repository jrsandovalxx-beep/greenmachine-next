"""The D-186 HR chance: a graded total mapped through the calibrated curve.

The curve lives in the configuration — measured anchors from the 42-slate
backtest (10,278 graded batter-days, no look-ahead), never a threshold the
source code invents. This module only interpolates: piecewise-linear
between neighboring anchors, holding the end values past both rails so the
display can never extrapolate steeper than the backtest measured. The grade
itself never reads the chance; the chance is a presentation of the total.
"""

from __future__ import annotations

import itertools
from decimal import Decimal

from greenmachine.config.schema import ChanceAnchor


def hr_chance(total_score: Decimal, anchors: tuple[ChanceAnchor, ...]) -> Decimal:
    """The calibrated chance (percent scale) a batter with this total homers
    on the slate day. Flat below the first anchor and above the last —
    the S band holds the top anchor's rate until a real S sample exists.
    """
    first, last = anchors[0], anchors[-1]
    if total_score <= first.score:
        return first.chance
    if total_score >= last.score:
        return last.chance
    for lower, upper in itertools.pairwise(anchors):
        if lower.score <= total_score <= upper.score:
            span = upper.score - lower.score
            position = (total_score - lower.score) / span
            return lower.chance + position * (upper.chance - lower.chance)
    raise AssertionError(  # validation guarantees the curve covers the domain
        f"total {total_score} fell between anchors — the curve must be increasing"
    )
