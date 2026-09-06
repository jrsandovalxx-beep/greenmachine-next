"""D-189 market-fetch policy: quiet hours, split keeps, and the memo.

Every expectation is derivable by hand from the policy constants: nothing
is spent before 2 PM Eastern, a priced board keeps twenty hours, an
absence keeps two, and a miss re-fetches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from greenmachine.odds import (
    ET,
    MARKET_ABSENCE_KEEP,
    MARKET_FIRST_CHECK_ET,
    MARKET_PRICED_KEEP,
    MarketMemo,
    in_market_quiet_hours,
    market_keep,
)


def test_quiet_hours_boundary_is_two_pm_eastern() -> None:
    just_before = datetime(2026, 9, 6, 17, 59, tzinfo=UTC)  # 1:59 PM ET
    on_the_dot = datetime(2026, 9, 6, 18, 0, tzinfo=UTC)  # 2:00 PM ET
    assert in_market_quiet_hours(just_before)
    assert not in_market_quiet_hours(on_the_dot)
    assert MARKET_FIRST_CHECK_ET.hour == 14


def test_quiet_hours_converts_the_callers_zone() -> None:
    morning_et = datetime(2026, 9, 6, 9, 30, tzinfo=ET)
    evening_et = datetime(2026, 9, 6, 19, 30, tzinfo=ET)
    assert in_market_quiet_hours(morning_et)
    assert not in_market_quiet_hours(evening_et)


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
