"""D-193 market-fetch policy: per-fixture sweep windows and the memo.

Every expectation is derivable by hand from the policy constants: a
fixture's sweep window opens two and a half hours before ITS first pitch
and closes forty-five minutes after it, a priced answer keeps twenty
hours, an absence keeps forty-five minutes, and a miss re-fetches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from greenmachine.odds import (
    MARKET_ABSENCE_KEEP,
    MARKET_CLOSE_GRACE,
    MARKET_PRICED_KEEP,
    MARKET_SWEEP_LEAD,
    MarketMemo,
    event_phase,
    market_keep,
)

FIRST_PITCH = datetime(2026, 9, 6, 23, 5, tzinfo=UTC)  # 7:05 PM ET


def test_the_sweep_window_opens_before_first_pitch() -> None:
    assert timedelta(hours=2, minutes=30) == MARKET_SWEEP_LEAD
    assert (
        event_phase(FIRST_PITCH, FIRST_PITCH - MARKET_SWEEP_LEAD - timedelta(minutes=1))
        == "pending"
    )
    assert event_phase(FIRST_PITCH, FIRST_PITCH - MARKET_SWEEP_LEAD) == "sweep"
    assert event_phase(FIRST_PITCH, FIRST_PITCH - timedelta(hours=1)) == "sweep"


def test_the_window_closes_after_a_short_post_start_grace() -> None:
    assert timedelta(minutes=45) == MARKET_CLOSE_GRACE
    assert (
        event_phase(FIRST_PITCH, FIRST_PITCH + MARKET_CLOSE_GRACE - timedelta(minutes=1)) == "sweep"
    )
    assert event_phase(FIRST_PITCH, FIRST_PITCH + MARKET_CLOSE_GRACE) == "closed"


def test_priced_answer_keeps_longer_than_an_absence() -> None:
    assert market_keep({"someone": object()}) == MARKET_PRICED_KEEP
    assert market_keep("not posted yet") == MARKET_ABSENCE_KEEP
    assert timedelta(hours=20) == MARKET_PRICED_KEEP
    assert timedelta(minutes=45) == MARKET_ABSENCE_KEEP


def test_memo_returns_the_kept_answer_until_it_expires() -> None:
    memo = MarketMemo()
    t0 = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
    memo.put("2026-09-06", "ev1", "not posted yet", t0)
    assert memo.get("2026-09-06", "ev1", t0 + timedelta(minutes=30)) == "not posted yet"
    assert memo.get("2026-09-06", "ev1", t0 + MARKET_ABSENCE_KEEP) is None


def test_memo_keeps_a_priced_answer_for_the_day() -> None:
    memo = MarketMemo()
    t0 = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
    priced = {"james wood": object()}
    memo.put("2026-09-06", "ev1", priced, t0)
    assert memo.get("2026-09-06", "ev1", t0 + timedelta(hours=19)) is priced
    assert memo.get("2026-09-06", "ev1", t0 + MARKET_PRICED_KEEP) is None


def test_memo_is_per_fixture_and_clears() -> None:
    memo = MarketMemo()
    t0 = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
    memo.put("2026-09-06", "ev1", "unavailable", t0)
    assert memo.get("2026-09-06", "ev2", t0) is None  # another fixture
    assert memo.get("2026-09-05", "ev1", t0) is None  # another slate day
    memo.clear()
    assert memo.get("2026-09-06", "ev1", t0) is None
