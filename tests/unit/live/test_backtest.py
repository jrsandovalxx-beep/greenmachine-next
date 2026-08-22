"""Backtest tallies and ROI arithmetic (D-095).

The regrade itself is pipeline build_board with an evening-prior as_of —
already covered in test_pipeline. Here: the grading moment, the outcome
pairing, the pooled tallies, and the odds arithmetic.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime
from decimal import Decimal

from synthetic_records import not_evaluable_grade_result
from test_pipeline import BATTER_ID, _build, _FakeApi, _FakeSavant

from greenmachine.live import backtest
from greenmachine.live.backtest import (
    BacktestRow,
    outcomes_for_day,
    profit_per_unit,
    roi_per_unit,
    slate_as_of,
    tally_grades,
)
from greenmachine.live.mlb_api import FetchFailure, GameLogEntry


def test_slate_as_of_is_the_prior_evening() -> None:
    """D-095: a past slate is graded the evening before, so nothing from the
    measured day can leak into the grade."""
    as_of = slate_as_of(date(2026, 8, 21))
    assert as_of == datetime(2026, 8, 20, backtest.BACKTEST_AS_OF_HOUR_UTC, tzinfo=UTC)


def _log(date: str, home_runs: int) -> dict[int, tuple[GameLogEntry, ...]]:
    return {
        BATTER_ID: (
            GameLogEntry(date=date, game_pk=777001, home_runs=home_runs, plate_appearances=4),
        )
    }


def test_outcomes_pair_each_graded_batter_with_the_slates_home_runs() -> None:
    """A batter homered when his game log records a home run on the slate
    date (D-100); a homer on any other day is not this slate's outcome."""
    board = _build(_FakeApi(), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    rows = outcomes_for_day(board, _log("2026-08-20", home_runs=1))
    # The fake slate fields the one batter on both lineups.
    assert len(rows) == 2
    assert all(row.homered for row in rows)
    assert all(row.slate_date == "2026-08-20" for row in rows)

    other_day = outcomes_for_day(board, _log("2026-08-19", home_runs=1))
    assert not any(row.homered for row in other_day)

    no_homer = outcomes_for_day(board, _log("2026-08-20", home_runs=0))
    assert not any(row.homered for row in no_homer)

    no_log = outcomes_for_day(board, {})
    assert not any(row.homered for row in no_log)


def test_outcomes_exclude_not_evaluable_batters() -> None:
    """Not-evaluable batters carry no grade — nothing to tally, excluded."""
    board = _build(_FakeApi(), _FakeSavant())
    assert not isinstance(board, FetchFailure)
    game = board.games[0]
    game = dataclasses.replace(
        game,
        home_batters=(
            dataclasses.replace(game.home_batters[0], result=not_evaluable_grade_result()),
        ),
    )
    board = dataclasses.replace(board, games=(game,))
    rows = outcomes_for_day(board, _log("2026-08-20", home_runs=1))
    assert len(rows) == 1
    assert rows[0].homered


def test_tally_grades_pools_in_ladder_order_with_named_empty_grades() -> None:
    rows = (
        BacktestRow("2026-08-20", "Able", "NYY", "S", True),
        BacktestRow("2026-08-20", "Baker", "NYY", "S", False),
        BacktestRow("2026-08-20", "Clark", "NYY", "A", True),
        BacktestRow("2026-08-21", "Davis", "NYY", "B", False),
        BacktestRow("2026-08-21", "Evans", "NYY", "B", True),
    )
    tallies = tally_grades(rows)
    assert [tally.grade for tally in tallies] == ["S", "A", "B", "C", "D"]
    tally_s, tally_a, tally_b, tally_c, _tally_d = tallies
    assert (tally_s.batters, tally_s.homered) == (2, 1)
    assert tally_s.hit_rate == Decimal("0.5")
    assert (tally_a.batters, tally_a.homered) == (1, 1)
    assert (tally_b.batters, tally_b.homered) == (2, 1)
    # No batter graded C: a named absence, never an invented zero.
    assert tally_c.batters == 0
    assert tally_c.hit_rate is None


def test_profit_per_unit_reads_american_odds() -> None:
    """+N pays N/100 per unit; -N pays 100/N; 0 is even money."""
    assert profit_per_unit(150) == Decimal("1.5")
    assert profit_per_unit(0) == Decimal(1)
    assert profit_per_unit(-110).quantize(Decimal("0.0001")) == Decimal("0.9091")


def test_roi_per_unit_prices_every_batter_as_a_unit_stake() -> None:
    # Even money at a 50% hit rate breaks even.
    assert roi_per_unit(Decimal("0.5"), 100) == Decimal(0)
    # +150 at 50%: 0.5 x 1.5 - 0.5 = 0.25.
    assert roi_per_unit(Decimal("0.5"), 150) == Decimal("0.25")
    # -110 at 50%: 0.5 x 100/110 - 0.5 ≈ -0.0455.
    assert roi_per_unit(Decimal("0.5"), -110).quantize(Decimal("0.0001")) == Decimal("-0.0455")
