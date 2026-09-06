"""D-190 market-fetch policy: the pre-game window and the memo.

Every expectation is derivable by hand from the policy constants: the paid
sweep opens one hour before first pitch, a priced board keeps twenty
hours, an absence keeps two, and a miss re-fetches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from greenmachine.odds import (
    MARKET_ABSENCE_KEEP,
    MARKET_PRE_GAME,
    MARKET_PRICED_KEEP,
    MarketMemo,
    market_keep,
)


def test_the_sweep_window_is_one_hour_before_first_pitch() -> None:
    assert timedelta(hours=1) == MARKET_PRE_GAME
    first_pitch = datetime(2026, 9, 6, 23, 5, tzinfo=UTC)  # 7:05 PM ET
    window_opens = first_pitch - MARKET_PRE_GAME
    before = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)  # a morning visit
    inside = datetime(2026, 9, 6, 22, 30, tzinfo=UTC)
    assert before < window_opens <= inside


def test_priced_board_keeps_longer_than_an_absence() -> None:
    assert market_keep({"someone": object()}) == MARKET_PRICED_KEEP
    assert market_keep("not posted yet") == MARKET_ABSENCE_KEEP
    assert timedelta(hours=20) == MARKET_PRICED_KEEP
    assert timedelta(hours=2) == MARKET_ABSENCE_KEEP


def test_memo_returns_the_kept_answer_until_it_expires() -> None:
    memo = MarketMemo()
    t0 = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
    memo.put("2026-09-06", "not posted yet", t0)
    assert memo.get("2026-09-06", t0 + timedelta(hours=1)) == "not posted yet"
    assert memo.get("2026-09-06", t0 + MARKET_ABSENCE_KEEP) is None


def test_memo_keeps_a_priced_board_for_the_day() -> None:
    memo = MarketMemo()
    t0 = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
    priced = {"james wood": object()}
    memo.put("2026-09-06", priced, t0)
    assert memo.get("2026-09-06", t0 + timedelta(hours=19)) is priced
    assert memo.get("2026-09-06", t0 + MARKET_PRICED_KEEP) is None


def test_memo_is_per_slate_date_and_clears() -> None:
    memo = MarketMemo()
    t0 = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
    memo.put("2026-09-06", "unavailable", t0)
    assert memo.get("2026-09-05", t0) is None
    memo.clear()
    assert memo.get("2026-09-06", t0) is None
