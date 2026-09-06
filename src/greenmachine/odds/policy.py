"""Market-fetch freshness policy (D-189): when to spend the owner's quota
and how long to keep each kind of answer.

The Odds API's free tier is 500 requests a month and one full-slate props
sweep costs one request per fixture (~15 on a full day), so the policy is
the whole ballgame:

- **Quiet hours before 2 PM ET.** Books post batter home-run props through
  the early afternoon; a morning sweep almost always comes back empty and
  still costs the full slate. Before 14:00 Eastern the app spends nothing
  and the column says "not posted yet".
- **A priced snapshot keeps 20 hours.** Once books are up, one sweep a day
  is enough — reruns never re-spend the quota.
- **An absence keeps 2 hours.** An empty afternoon sweep retries at the
  next visit two hours later, so props that post late still land the same
  day. Typical month lands near the free cap (~430-490 requests); a heavy
  month can trip it, which degrades the column to "unavailable" until the
  reset — the signal to revisit the plan, never a breakage.

The memo is a plain in-process store: the deployment is one Streamlit
process, and the policy lives here — tested — instead of inside a cache
decorator whose TTL cannot depend on the answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# First spend of the day: books have largely posted batter props by 2 PM ET.
MARKET_FIRST_CHECK_ET = time(14, 0)

# How long each kind of answer is kept before the next visit re-fetches.
MARKET_PRICED_KEEP = timedelta(hours=20)
MARKET_ABSENCE_KEEP = timedelta(hours=2)


def in_market_quiet_hours(now: datetime) -> bool:
    """True while the feed is almost certainly still empty — before 2 PM
    Eastern on the visitor's clock. The comparison is on Eastern wall time,
    whatever zone the caller's timestamp carries."""
    return now.astimezone(ET).time() < MARKET_FIRST_CHECK_ET


def market_keep(value: Mapping[str, Any] | str) -> timedelta:
    """The keep for a snapshot answer: a priced board (mapping) gets the
    long keep; any named absence (string) gets the short retry."""
    return MARKET_PRICED_KEEP if isinstance(value, Mapping) else MARKET_ABSENCE_KEEP


@dataclass
class _MemoEntry:
    stored_at: datetime
    value: Mapping[str, Any] | str


class MarketMemo:
    """One day's market answer per slate date, kept for its policy TTL."""

    def __init__(self) -> None:
        self._entries: dict[str, _MemoEntry] = {}

    def get(self, slate_date: str, now: datetime) -> Mapping[str, Any] | str | None:
        """The kept answer, or None when absent or expired. A None miss can
        also be returned for a legitimately empty memo — callers treat every
        miss as a fetch, so conflating the two is correct here."""
        entry = self._entries.get(slate_date)
        if entry is None:
            return None
        if now - entry.stored_at >= market_keep(entry.value):
            del self._entries[slate_date]
            return None
        return entry.value

    def put(self, slate_date: str, value: Mapping[str, Any] | str, now: datetime) -> None:
        self._entries[slate_date] = _MemoEntry(stored_at=now, value=value)

    def clear(self) -> None:
        self._entries.clear()
