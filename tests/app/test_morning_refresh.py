"""D-136 (PO): the morning refresh — the season sources day-anchor at noon
UTC, the day-event cache splits by finality, and a fetch failure never
poisons an anchored day.

Everything here drives the proxies and the cached dispatcher directly with
recording fakes — no sockets, no Streamlit runtime.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import streamlit as st
import streamlit_app

from greenmachine.live.mlb_api import FetchFailure


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    st.cache_data.clear()


class _RecordingSavant:
    """Stands in for BaseballSavant: counts the season-board fetches and
    answers with a sentinel; the per-day feed counts separately so the
    split-by-finality routing is visible."""

    def __init__(self) -> None:
        self.season_calls = 0
        self.day_calls: list[str] = []
        self.fail_next = False

    def fetch_expected_stats(self, *, year: int) -> object:
        self.season_calls += 1
        if self.fail_next:
            self.fail_next = False
            return FetchFailure("a morning transient")
        return {"expected": year}

    def fetch_pitch_events(self, *, year: int, day: str) -> object:
        self.day_calls.append(day)
        return (f"pitches-{day}",)


class _RecordingApi:
    """Stands in for MlbStatsApi: the two season fetches count; the slate
    fetch proves it is never wrapped."""

    def __init__(self) -> None:
        self.season_calls = 0
        self.slate_calls = 0

    def fetch_season_hitting(self, player_ids: tuple[int, ...]) -> object:
        self.season_calls += 1
        return {pid: "line" for pid in player_ids}

    def fetch_slate(self, date_mmddyyyy: str) -> object:
        self.slate_calls += 1
        return f"slate-{date_mmddyyyy}"


def _wire(monkeypatch: pytest.MonkeyPatch) -> tuple[_RecordingApi, _RecordingSavant]:
    api, savant = _RecordingApi(), _RecordingSavant()
    monkeypatch.setattr(
        streamlit_app,
        "live_mlb_adapters",
        lambda: (api, savant),  # type: ignore[return-value]
    )
    return api, savant


def test_the_anchor_flips_at_noon_utc() -> None:
    """The PO's "refresh every morning": before the flip the board trusts
    yesterday's season data; at and after it, today's. Noon UTC is 5 AM in
    Arizona, where the board is read."""
    before = datetime(2026, 8, 26, 11, 59, tzinfo=UTC)
    at = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    after_midnight = datetime(2026, 8, 26, 0, 30, tzinfo=UTC)
    assert streamlit_app._season_data_anchor(before) == "2026-08-25"
    assert streamlit_app._season_data_anchor(after_midnight) == "2026-08-25"
    assert streamlit_app._season_data_anchor(at) == "2026-08-26"


def test_a_season_board_fetches_once_per_anchor_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two builds inside one anchor day share one fetch; the morning flip —
    and only the flip — refetches."""
    _api, savant = _wire(monkeypatch)
    wrapped = streamlit_app._DayAnchoredSavant(savant, "2026-08-26")  # type: ignore[arg-type]
    assert wrapped.fetch_expected_stats(year=2026) == {"expected": 2026}
    assert wrapped.fetch_expected_stats(year=2026) == {"expected": 2026}
    assert savant.season_calls == 1
    tomorrow = streamlit_app._DayAnchoredSavant(savant, "2026-08-27")  # type: ignore[arg-type]
    assert tomorrow.fetch_expected_stats(year=2026) == {"expected": 2026}
    assert savant.season_calls == 2


def test_a_failed_season_fetch_is_never_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """A morning transient must not poison the anchored day: the proxy
    hands the pipeline its ordinary FetchFailure, and the very next build
    asks the source again."""
    _api, savant = _wire(monkeypatch)
    wrapped = streamlit_app._DayAnchoredSavant(savant, "2026-08-26")  # type: ignore[arg-type]
    savant.fail_next = True
    failed = wrapped.fetch_expected_stats(year=2026)
    assert isinstance(failed, FetchFailure)
    assert "morning transient" in failed.reason
    assert wrapped.fetch_expected_stats(year=2026) == {"expected": 2026}
    assert savant.season_calls == 2


def test_the_mlb_season_fetches_anchor_but_the_slate_stays_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Season hitting/pitching ride the anchor; the slate is the day itself
    and is never cached by the proxy — two asks, two fetches."""
    api, _savant = _wire(monkeypatch)
    wrapped = streamlit_app._DayAnchoredMlbApi(api, "2026-08-26")  # type: ignore[arg-type]
    assert wrapped.fetch_season_hitting((1, 2)) == {1: "line", 2: "line"}
    assert wrapped.fetch_season_hitting((1, 2)) == {1: "line", 2: "line"}
    assert api.season_calls == 1
    assert wrapped.fetch_slate("08/26/2026") == "slate-08/26/2026"
    assert wrapped.fetch_slate("08/26/2026") == "slate-08/26/2026"
    assert api.slate_calls == 2


def test_day_events_route_by_finality(monkeypatch: pytest.MonkeyPatch) -> None:
    """A day before the anchor is final and takes the long cache; the
    anchor day itself still resolves and keeps the hourly read. Yesterday
    becomes final exactly when the morning update lands."""
    _api, savant = _wire(monkeypatch)
    assert streamlit_app._day_events("2026-08-25", 2026, "2026-08-26") == ("pitches-2026-08-25",)
    assert streamlit_app._day_events("2026-08-26", 2026, "2026-08-26") == ("pitches-2026-08-26",)
    assert savant.day_calls == ["2026-08-25", "2026-08-26"]
    # The final day caches long: a second read does not refetch; the
    # resolving day also caches, under its own shorter bound.
    streamlit_app._day_events("2026-08-25", 2026, "2026-08-26")
    streamlit_app._day_events("2026-08-26", 2026, "2026-08-26")
    assert savant.day_calls == ["2026-08-25", "2026-08-26"]
