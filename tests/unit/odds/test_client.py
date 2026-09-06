"""D-187 odds client suite, driven by synthetic feeds — no sockets (GM-008).

Every expectation below is derivable by hand from the fixture payloads: the
de-vig is two implied shares normalized, the snapshot averages the books
that priced the batter, and every absence is named rather than invented.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from greenmachine.live.mlb_api import FetchFailure
from greenmachine.live.transport import HttpResponse, TransportUnreachableError
from greenmachine.odds import (
    NO_PROPS_REASON,
    MarketRead,
    TheOddsApi,
    market_snapshot,
    normalize_name,
)

DAY = date(2026, 9, 5)  # 2026-09-06T01:10Z is still the 9/5 slate in Phoenix

_EVENTS = [
    {
        "id": "ev1",
        "commence_time": "2026-09-06T01:10:00Z",
        "home_team": "Arizona Diamondbacks",
        "away_team": "Los Angeles Dodgers",
    },
    {
        "id": "ev2",
        "commence_time": "2026-09-05T17:05:00Z",
        "home_team": "New York Yankees",
        "away_team": "Boston Red Sox",
    },
    {
        "id": "ev3",  # next UTC day's slate — not this slate day in Phoenix
        "commence_time": "2026-09-06T23:05:00Z",
        "home_team": "Chicago Cubs",
        "away_team": "St. Louis Cardinals",
    },
]

_PROPS_EV1 = {
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [
                {
                    "key": "batter_home_runs",
                    "outcomes": [
                        {
                            "name": "Over",
                            "description": "Shohei Ohtani",
                            "price": 2.98,
                            "point": 0.5,
                        },
                        {
                            "name": "Under",
                            "description": "Shohei Ohtani",
                            "price": 1.40,
                            "point": 0.5,
                        },
                        # An alternate ladder rung — never the headline read.
                        {
                            "name": "Over",
                            "description": "Shohei Ohtani",
                            "price": 5.0,
                            "point": 1.5,
                        },
                        {
                            "name": "Over",
                            "description": "Freddie Freeman",
                            "price": 4.39,
                            "point": 0.5,
                        },
                        {
                            "name": "Under",
                            "description": "Freddie Freeman",
                            "price": 1.25,
                            "point": 0.5,
                        },
                    ],
                }
            ],
        },
        {
            "key": "fanduel",
            "markets": [
                {
                    "key": "batter_home_runs",
                    "outcomes": [
                        {
                            "name": "Over",
                            "description": "Shohei Ohtani",
                            "price": 3.10,
                            "point": 0.5,
                        },
                        {
                            "name": "Under",
                            "description": "Shohei Ohtani",
                            "price": 1.38,
                            "point": 0.5,
                        },
                    ],
                }
            ],
        },
        {
            "key": "betmgm",  # priced the ladder only — no read
            "markets": [
                {
                    "key": "batter_home_runs",
                    "outcomes": [
                        {
                            "name": "Over",
                            "description": "Shohei Ohtani",
                            "price": 6.0,
                            "point": 2.5,
                        },
                    ],
                }
            ],
        },
    ]
}

_PROPS_EV2 = {"bookmakers": []}  # props not posted yet for this fixture


class _FakeTransport:
    """Answers by URL shape; records every request."""

    def __init__(self, routes: dict[str, tuple[int, object]]) -> None:
        self._routes = routes
        self.requested_urls: list[str] = []

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.requested_urls.append(url)
        for marker, (status, payload) in self._routes.items():
            if marker in url:
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                return HttpResponse(status=status, body=body)
        raise AssertionError(f"unexpected URL: {url}")


def _api(routes: dict[str, tuple[int, object]]) -> TheOddsApi:
    return TheOddsApi(_FakeTransport(routes), api_key="TESTKEY")


def _routes() -> dict[str, tuple[int, object]]:
    return {
        "/events?": (200, _EVENTS),
        "/events/ev1/odds": (200, _PROPS_EV1),
        "/events/ev2/odds": (200, _PROPS_EV2),
    }


def _fair(over: str, under: str) -> Decimal:
    implied = 1 / Decimal(over)
    return implied / (implied + 1 / Decimal(under))


def test_normalize_name_folds_accents_and_punctuation() -> None:
    assert normalize_name("José Ramírez") == "joseramirez"
    assert normalize_name("Shohei Ohtani") == "shoheiohtani"
    assert normalize_name("D'Angelo Ortiz Jr.") == "dangeloortizjr"


def test_events_keeps_only_the_slate_day() -> None:
    events = _api(_routes()).fetch_events(DAY)
    assert not isinstance(events, FetchFailure)
    assert [event.event_id for event in events] == ["ev1", "ev2"]


def test_events_carry_first_pitch_for_the_freshness_gate() -> None:
    """D-190: the paid sweep opens one hour before the earliest commence —
    the events list is free, so the gate spends nothing."""
    events = _api(_routes()).fetch_events(DAY)
    assert not isinstance(events, FetchFailure)
    first_pitch = min(event.commence_time for event in events)
    assert first_pitch == datetime(2026, 9, 5, 17, 5, tzinfo=UTC)


def test_props_devig_and_skip_the_ladder() -> None:
    reads = _api(_routes()).fetch_hr_props("ev1")
    assert not isinstance(reads, FetchFailure)
    assert set(reads) == {
        ("shoheiohtani", "draftkings", _fair("2.98", "1.40")),
        ("shoheiohtani", "fanduel", _fair("3.10", "1.38")),
        ("freddiefreeman", "draftkings", _fair("4.39", "1.25")),
    }


def test_snapshot_averages_books_and_counts_them() -> None:
    snapshot = market_snapshot(_api(_routes()), DAY)
    assert not isinstance(snapshot, FetchFailure)
    ohtani = snapshot["shoheiohtani"]
    want = (_fair("2.98", "1.40") + _fair("3.10", "1.38")) / 2 * 100
    assert ohtani.fair_percent == want.quantize(Decimal("0.0001"))
    assert ohtani.books == 2
    assert snapshot["freddiefreeman"].books == 1


def test_snapshot_names_an_unpriced_slate() -> None:
    routes = _routes()
    routes["/events/ev1/odds"] = (200, {"bookmakers": []})
    result = market_snapshot(_api(routes), DAY)
    assert isinstance(result, FetchFailure)
    assert result.reason == NO_PROPS_REASON


def test_a_fixture_failure_degrades_out_of_the_average() -> None:
    routes = _routes()
    routes["/events/ev2/odds"] = (500, b"server error")
    snapshot = market_snapshot(_api(routes), DAY)
    assert not isinstance(snapshot, FetchFailure)
    assert "shoheiohtani" in snapshot


def test_an_events_failure_fails_the_snapshot() -> None:
    routes = {"/events?": (429, b"quota exhausted")}
    result = market_snapshot(_api(routes), DAY)
    assert isinstance(result, FetchFailure)
    assert "HTTP 429" in result.reason


def test_transport_errors_become_named_failures() -> None:
    class _Down:
        def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
            raise TransportUnreachableError("dns failed")

    api = TheOddsApi(_Down(), api_key="TESTKEY")
    result = api.fetch_events(DAY)
    assert isinstance(result, FetchFailure)
    assert "TransportUnreachableError" in result.reason
    assert "TESTKEY" not in result.reason  # the key never leaves the request URL


def test_a_non_json_answer_is_a_named_failure() -> None:
    routes = {"/events?": (200, b"<html>not the feed</html>")}
    result = _api(routes).fetch_events(DAY)
    assert isinstance(result, FetchFailure)
    assert "not JSON" in result.reason


def test_a_one_sided_book_has_no_read() -> None:
    payload = {
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "batter_home_runs",
                        "outcomes": [
                            {"name": "Over", "description": "A Batter", "price": 3.0, "point": 0.5},
                        ],
                    }
                ],
            }
        ]
    }
    reads = _api({"/events/ev1/odds": (200, payload)}).fetch_hr_props("ev1")
    assert not isinstance(reads, FetchFailure)
    assert reads == ()


def test_a_price_at_or_below_even_is_malformed() -> None:
    payload = {
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "batter_home_runs",
                        "outcomes": [
                            {"name": "Over", "description": "A Batter", "price": 1.0, "point": 0.5},
                            {
                                "name": "Under",
                                "description": "A Batter",
                                "price": 1.4,
                                "point": 0.5,
                            },
                        ],
                    }
                ],
            }
        ]
    }
    result = _api({"/events/ev1/odds": (200, payload)}).fetch_hr_props("ev1")
    assert isinstance(result, FetchFailure)
    assert "not a valid decimal odd" in result.reason


def test_the_market_read_is_immutable() -> None:
    read = MarketRead(fair_percent=Decimal("14.4"), books=3)
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        read.books = 4  # type: ignore[misc]
