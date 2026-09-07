"""Market-fetch freshness policy (D-189/D-190, restructured by D-193): when
to spend the owner's quota and how long to keep each kind of answer.

The Odds API's free tier is 500 requests a month and pricing one fixture
costs one request, so the policy is the whole ballgame. D-190 swept the
slate once a day an hour before its FIRST pitch — which priced the evening
games but never the afternoon ones (books pull a game's props at its first
pitch, and by the evening sweep those markets are gone). D-193 (PO: "make
sure we have odds for all games") sweeps in CLUSTERS instead: every fixture
is priced once, close to its own first pitch, when its window opens:

- **Pending — before first pitch minus the lead:** no paid call for this
  fixture; its batters read "not posted yet". The events list that carries
  first-pitch times is free, so the gate itself never spends.
- **Sweep — inside the window:** price the fixture once; the answer keeps
  20 hours, so reruns never re-spend. A fixture still unswept at first
  pitch gets one grace attempt (props linger a few minutes), then the
  market is closed and no visit will spend on it again.
- **An empty or failed sweep keeps 45 minutes**, so the next scheduled
  trigger retries it — books occasionally post a fixture late, and the
  triggers land every couple of hours through the day.

Expected spend: one request per fixture on a normal game day (~10-16),
plus a rare retry when a window opens before the books post — inside the
free tier with margin, by design. The day's cluster triggers are the wake
workflow's schedule; the policy here is trigger-agnostic.

The memo is a plain in-process store: the deployment is one Streamlit
process, and the policy lives here — tested — instead of inside a cache
decorator whose TTL cannot depend on the answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

# D-193: a fixture's sweep window opens this long before ITS first pitch —
# early enough that the day's cluster triggers always catch it inside the
# window, late enough that the line is the near-final, decision-relevant
# one. The one-hour read D-190 picked remains the typical sweep time; the
# lead only widens the catch window so no trigger cadence can miss it.
MARKET_SWEEP_LEAD = timedelta(hours=2, minutes=30)

# D-193: after first pitch the books pull the market within minutes. One
# post-start attempt is still allowed inside this grace (a just-started
# fixture often still answers), then the fixture is closed and free.
MARKET_CLOSE_GRACE = timedelta(minutes=45)

# How long each kind of answer is kept before the next visit re-fetches.
MARKET_PRICED_KEEP = timedelta(hours=20)
MARKET_ABSENCE_KEEP = timedelta(minutes=45)


def market_keep(value: Mapping[str, Any] | str) -> timedelta:
    """The keep for one fixture's answer: priced reads (mapping) get the
    long keep; any named absence (string) gets the short retry."""
    return MARKET_PRICED_KEEP if isinstance(value, Mapping) else MARKET_ABSENCE_KEEP


def event_phase(commence: datetime, now: datetime) -> Literal["pending", "sweep", "closed"]:
    """Where one fixture stands against the sweep clock: before its window
    (pending — free), inside it (sweep — one paid call), or past the grace
    (closed — never spend again)."""
    if now < commence - MARKET_SWEEP_LEAD:
        return "pending"
    if now < commence + MARKET_CLOSE_GRACE:
        return "sweep"
    return "closed"


@dataclass
class _MemoEntry:
    stored_at: datetime
    value: Mapping[str, Any] | str


class MarketMemo:
    """Market answers per (slate date, fixture), kept for the policy TTL."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], _MemoEntry] = {}

    def get(self, slate_date: str, event_id: str, now: datetime) -> Mapping[str, Any] | str | None:
        """The kept answer, or None when absent or expired. A None miss can
        also be returned for a legitimately empty memo — callers treat every
        miss as a fetch, so conflating the two is correct here."""
        entry = self._entries.get((slate_date, event_id))
        if entry is None:
            return None
        if now - entry.stored_at >= market_keep(entry.value):
            del self._entries[(slate_date, event_id)]
            return None
        return entry.value

    def put(
        self, slate_date: str, event_id: str, value: Mapping[str, Any] | str, now: datetime
    ) -> None:
        self._entries[(slate_date, event_id)] = _MemoEntry(stored_at=now, value=value)

    def clear(self) -> None:
        self._entries.clear()
