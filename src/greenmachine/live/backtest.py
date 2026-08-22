"""Backtest helpers — regrade past slates and tally grade outcomes (D-095).

The backtest answers one question: on past slates, how often did a batter
carrying each grade homer that day? A past slate is regraded with an as-of
of the prior evening, so no event from the measured day can leak into the
grade, then every graded batter is paired with that day's outcome.

Named approximations, each named on screen (D-023/D-025):

- Season boards (hitting lines, pitch arsenals, statcast) are current
  snapshots: regrading a past date reads today's season rows, not the rows
  as they stood that day.
- Weather is not reconstructed: temperature and wind are absent on backtest
  boards and the affected components name that absence as usual.
- ROI is arithmetic on odds the viewer enters; there is no odds source.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from greenmachine.domain.grade_result import EvaluatedGradeResult
from greenmachine.live.mlb_api import GameLogEntry
from greenmachine.live.pipeline import SlateBoard

# Grading moment for a backtested slate: 20:00 UTC the prior evening — after
# that day's games, before any slate-day game — so the measured day's events
# cannot leak into the grade.
BACKTEST_AS_OF_HOUR_UTC = 20

# Pooled tally order: the grade ladder, best first.
GRADE_ORDER: tuple[str, ...] = ("S", "A", "B", "C", "D")


def slate_as_of(slate_date: date) -> datetime:
    """The grading moment for a past slate: 20:00 UTC the prior evening."""
    return datetime.combine(
        slate_date - timedelta(days=1), time(BACKTEST_AS_OF_HOUR_UTC), tzinfo=UTC
    )


@dataclass(frozen=True)
class BacktestRow:
    """One graded batter on one past slate, paired with that day's outcome."""

    slate_date: str
    full_name: str
    team: str
    grade: str
    homered: bool


def outcomes_for_day(
    board: SlateBoard, game_logs: dict[int, tuple[GameLogEntry, ...]]
) -> tuple[BacktestRow, ...]:
    """Pair every evaluated batter on the board with his slate-day outcome.

    A batter homered when his game log records a home run on the slate
    date (D-100): the log is near-real-time and covers completed games
    only, so a past slate's outcomes are final and complete. Not-evaluable
    batters carry no grade, so there is nothing to tally — they are
    excluded, and the view names that.
    """
    homered_ids = {
        player_id
        for player_id, entries in game_logs.items()
        if any(entry.date == board.official_date and entry.home_runs > 0 for entry in entries)
    }
    rows: list[BacktestRow] = []
    for game in board.games:
        for card in (*game.away_batters, *game.home_batters):
            result = card.result
            if not isinstance(result, EvaluatedGradeResult):
                continue
            rows.append(
                BacktestRow(
                    slate_date=board.official_date,
                    full_name=card.full_name,
                    team=card.team,
                    grade=result.grade.value,
                    homered=card.player_id in homered_ids,
                )
            )
    return tuple(rows)


@dataclass(frozen=True)
class GradeTally:
    """A pooled tally for one grade letter across backtested slates."""

    grade: str
    batters: int
    homered: int

    @property
    def hit_rate(self) -> Decimal | None:
        """Homered per batter; None when no batter carried the grade."""
        if self.batters == 0:
            return None
        return Decimal(self.homered) / Decimal(self.batters)


def tally_grades(rows: tuple[BacktestRow, ...]) -> tuple[GradeTally, ...]:
    """Pool outcome rows by grade letter, in ladder order (S first)."""
    return tuple(
        GradeTally(
            grade=grade,
            batters=sum(1 for row in rows if row.grade == grade),
            homered=sum(1 for row in rows if row.grade == grade and row.homered),
        )
        for grade in GRADE_ORDER
    )


def profit_per_unit(american_odds: int) -> Decimal:
    """Profit on a winning 1-unit stake at American odds; 0 is even money."""
    if american_odds == 0:
        return Decimal(1)
    if american_odds > 0:
        return Decimal(american_odds) / Decimal(100)
    return Decimal(100) / Decimal(-american_odds)


def roi_per_unit(hit_rate: Decimal, american_odds: int) -> Decimal:
    """Expected ROI per 1-unit stake at a pooled hit rate and American odds.

    Every graded batter is treated as a 1-unit stake: winners return the
    odds' profit, losers return -1. The odds are the viewer's own entry —
    the product holds no odds source (D-095).
    """
    return hit_rate * profit_per_unit(american_odds) - (1 - hit_rate)
