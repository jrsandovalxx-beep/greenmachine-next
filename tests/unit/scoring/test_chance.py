"""D-186 HR-chance interpolation suite.

The anchors below are synthetic (a plain 2-4-6 ramp), never the production
curve — the production anchors are pinned verbatim in
tests/unit/config/test_production_tables.py.
"""

from __future__ import annotations

import itertools
from decimal import Decimal

import pytest

from greenmachine.config.schema import ChanceAnchor
from greenmachine.scoring import hr_chance


def _anchor(score: str, chance: str) -> ChanceAnchor:
    # ConfigDecimal takes the quoted string — configuration is parsed from
    # text, never handed pre-built numbers.
    return ChanceAnchor(score=score, chance=chance)


RAMP = (_anchor("2", "10"), _anchor("4", "20"), _anchor("6", "30"))


def test_holds_first_anchor_below_the_rail() -> None:
    assert hr_chance(Decimal("0"), RAMP) == Decimal("10")
    assert hr_chance(Decimal("2"), RAMP) == Decimal("10")


def test_holds_last_anchor_above_the_rail() -> None:
    assert hr_chance(Decimal("6"), RAMP) == Decimal("30")
    assert hr_chance(Decimal("11.3"), RAMP) == Decimal("30")


def test_interpolates_linearly_between_anchors() -> None:
    # Score 3 sits halfway between (2, 10) and (4, 20) → 15.
    assert hr_chance(Decimal("3"), RAMP) == Decimal("15")
    # Score 5 sits halfway between (4, 20) and (6, 30) → 25.
    assert hr_chance(Decimal("5"), RAMP) == Decimal("25")


def test_hits_anchor_points_exactly() -> None:
    assert hr_chance(Decimal("4"), RAMP) == Decimal("20")


def test_flat_segment_stays_flat() -> None:
    plateau = (_anchor("1", "5"), _anchor("3", "9"), _anchor("5", "9"))
    assert hr_chance(Decimal("4"), plateau) == Decimal("9")


def test_curve_is_monotone_across_the_domain() -> None:
    anchors = (
        _anchor("1", "3.6"),
        _anchor("2.5", "5.7"),
        _anchor("3.5", "6.5"),
        _anchor("4.5", "10.3"),
    )
    steps = [Decimal(i) / Decimal(10) for i in range(0, 61)]
    chances = [hr_chance(step, anchors) for step in steps]
    assert all(a <= b for a, b in itertools.pairwise(chances))


def test_empty_anchors_raise() -> None:
    with pytest.raises(IndexError):
        hr_chance(Decimal("5"), ())
