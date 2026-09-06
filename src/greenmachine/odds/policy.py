"""Market-fetch freshness policy (D-189/D-190): when to spend the owner's
quota and how long to keep each kind of answer.

The Odds API's free tier is 500 requests a month and one full-slate props
sweep costs one request per fixture (~15 on a full day), so the policy is
the whole ballgame. The schedule is the PO's (D-190): **one paid sweep a
day, opening an hour before the slate's first pitch** — the moment the
books' props are both posted and decision-relevant. The events list that
carries first-pitch times is free, so the gate costs nothing and every
visit can check it:

- **Before first pitch minus one hour:** no paid call; the column says
  "not posted yet". Morning visits and the 5 AM wake never spend.
- **At or inside the window:** sweep once; a priced board keeps 20 hours,
  so reruns never re-spend.
- **An empty or failed sweep keeps 2 hours**, then the next visit retries
  — props that post inside the last hour still land the same day. (Rare:
  books have normally posted by the window.)

Expected spend: ~15 requests on a normal game day (~450 a month with the
off-days), plus one retry sweep on the rare day the window opens empty —
inside the free tier with margin, by design.

The memo is a plain in-process store: the deployment is one Streamlit
process, and the policy lives here — tested — instead of inside a cache
decorator whose TTL cannot depend on the answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# D-190 (PO): the paid sweep opens one hour before the slate's first pitch.
MARKET_PRE_GAME = timedelta(hours=1)

# How long each kind of answer is kept before the next visit re-fetches.
MARKET_PRICED_KEEP = timedelta(hours=20)
MARKET_ABSENCE_KEEP = timedelta(hours=2)


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
