"""§GMF-005 submission 1: the live adapter, proven without a socket.

Every payload here is **synthetic and shaped like the API** — hand-authored from
the documented response shape, never a recorded live response (the section's own
rule, stricter than D-052's licensed-provider scope, and followed because the
plan text governs). Values are deliberately non-baseball (OQ-4): a 321 °F
reading is a validation artifact nobody can mistake for weather.

Nothing in this file touches the network, and nothing asks GM-008 for a
carve-out. The adapter takes a ``Transport``, so a fake answers every call; the
suite-wide guard stays armed, and the only thing that ever opens a connection is
the deployed application, which is what submission 2 exists to observe.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from greenmachine.common.clock import Clock, FixedClock
from greenmachine.inputs import AbsenceReason, ParkVenue, VenueType
from greenmachine.weather import WeatherAdapter
from greenmachine.weather.nws import (
    DEFAULT_CONTACT,
    FORECAST_FRESHNESS,
    MAX_ATTEMPTS,
    RETRY_DELAY_SECONDS,
    SOURCE_ID,
    NwsWeatherAdapter,
)
from greenmachine.weather.transport import (
    NWS_HOST,
    HttpResponse,
    TransportTimeoutError,
    TransportUnreachableError,
)

START = datetime(2026, 8, 19, 18, 0, 0, tzinfo=UTC)

FORECAST_URL = f"https://{NWS_HOST}/gridpoints/SYN/1,2/forecast/hourly"

VENUE = ParkVenue(
    "synthetic-park",
    "Synthetic Park",
    "Synthetic Club",
    VenueType.OPEN_AIR,
    None,
    latitude=Decimal("40.830"),
    longitude=Decimal("-73.926"),
)
OTHER_VENUE = ParkVenue(
    "other-park",
    "Other Park",
    "Other Club",
    VenueType.OPEN_AIR,
    None,
    latitude=Decimal("41.948"),
    longitude=Decimal("-87.655"),
)


def points_body(forecast_url: str = FORECAST_URL) -> bytes:
    return json.dumps({"properties": {"forecastHourly": forecast_url}}).encode()


def forecast_body(periods: list[dict[str, object]] | None = None) -> bytes:
    if periods is None:
        periods = [
            {
                "temperature": 321,
                "windSpeed": "88 mph",
                "windDirection": "NNE",
                "shortForecast": "Synthetic sky (OQ-4)",
            }
        ]
    return json.dumps({"properties": {"periods": periods}}).encode()


class FakeTransport:
    """Answers from a scripted queue, and records every request it received."""

    def __init__(self, script: list[object]) -> None:
        self.script = list(script)
        self.urls: list[str] = []
        self.headers: list[dict[str, str]] = []

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.urls.append(url)
        self.headers.append(dict(headers))
        if not self.script:
            raise AssertionError(f"unscripted request to {url}")
        answer = self.script.pop(0)
        if isinstance(answer, Exception):
            raise answer
        assert isinstance(answer, HttpResponse)
        return answer


class StepClock:
    """A clock the test advances by hand. Never reads wall-clock time."""

    def __init__(self, start: datetime = START) -> None:
        self.moment = start

    def now(self) -> datetime:
        return self.moment

    def advance(self, delta: timedelta) -> None:
        self.moment += delta


class RecordingSleeper:
    """Records the delays asked for. **No test ever waits.**"""

    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def build(
    script: list[object], clock: Clock | None = None
) -> tuple[NwsWeatherAdapter, FakeTransport, RecordingSleeper]:
    transport = FakeTransport(script)
    sleeper = RecordingSleeper()
    adapter = NwsWeatherAdapter(
        transport=transport,
        clock=clock if clock is not None else FixedClock(START),
        sleep=sleeper,
    )
    return adapter, transport, sleeper


def ok(body: bytes) -> HttpResponse:
    return HttpResponse(status=200, body=body)


# --- the seam ---------------------------------------------------------------


def test_the_live_adapter_satisfies_the_same_seam_the_fixture_does() -> None:
    """Structural conformance, checked rather than declared — §GMF-005 binds
    behind the interface §GMF-004 built, and nothing about the screen changes."""
    adapter, _, _ = build([ok(points_body()), ok(forecast_body())])
    bound: WeatherAdapter = adapter
    assert bound.forecast_for(VENUE).value is not None


def test_a_forecast_carries_its_values_and_the_time_it_was_obtained() -> None:
    adapter, _, _ = build([ok(points_body()), ok(forecast_body())])
    field = adapter.forecast_for(VENUE)
    forecast = field.value
    assert forecast is not None
    assert forecast.temperature_f == Decimal("321")
    assert forecast.wind_speed_mph == Decimal("88")
    assert forecast.wind_direction == "NNE"
    assert forecast.obtained_at == START
    assert field.source_id == SOURCE_ID
    assert field.derivation is None  # sourced, never computed


def test_a_wind_range_takes_its_first_number() -> None:
    """NWS reports ``5 to 10 mph``; a naive parse would raise and lose a value
    that is perfectly readable."""
    periods = [
        {
            "temperature": 300,
            "windSpeed": "7 to 21 mph",
            "windDirection": "SW",
            "shortForecast": "Synthetic",
        }
    ]
    adapter, _, _ = build([ok(points_body()), ok(forecast_body(periods))])
    forecast = adapter.forecast_for(VENUE).value
    assert forecast is not None
    assert forecast.wind_speed_mph == Decimal("7")


# --- the four named failure modes, each exercised ---------------------------


def test_timeout_maps_to_source_unavailable() -> None:
    adapter, _, _ = build([TransportTimeoutError("timed out")])
    field = adapter.forecast_for(VENUE)
    assert field.value is None
    assert field.absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert field.source_id == SOURCE_ID
    assert "timed out" in adapter.diagnostics()[VENUE.venue_id]


def test_a_non_200_maps_to_source_unavailable() -> None:
    adapter, _, _ = build([HttpResponse(status=404, body=b"")])
    field = adapter.forecast_for(VENUE)
    assert field.absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert "outside the coverage area" in adapter.diagnostics()[VENUE.venue_id]


def test_a_malformed_payload_maps_to_source_unavailable() -> None:
    adapter, _, _ = build([ok(b"{not json at all")])
    field = adapter.forecast_for(VENUE)
    assert field.absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert "unreadable payload" in adapter.diagnostics()[VENUE.venue_id]


def test_a_well_formed_payload_missing_a_field_is_still_unreadable() -> None:
    periods = [{"temperature": 300, "windDirection": "SW", "shortForecast": "Synthetic"}]
    adapter, _, _ = build([ok(points_body()), ok(forecast_body(periods))])
    assert adapter.forecast_for(VENUE).absence is AbsenceReason.SOURCE_UNAVAILABLE


def test_a_rate_limit_survives_one_retry_then_maps_to_source_unavailable() -> None:
    limited = HttpResponse(status=429, body=b"")
    adapter, transport, sleeper = build([limited, limited])
    field = adapter.forecast_for(VENUE)
    assert field.absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert "rate-limited" in adapter.diagnostics()[VENUE.venue_id]
    assert len(transport.urls) == MAX_ATTEMPTS == 2
    assert sleeper.delays == [RETRY_DELAY_SECONDS]  # one delay, and no test waited


def test_an_unreachable_source_maps_to_source_unavailable() -> None:
    adapter, _, _ = build([TransportUnreachableError("dns failure")])
    field = adapter.forecast_for(VENUE)
    assert field.absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert "could not be reached" in adapter.diagnostics()[VENUE.venue_id]


# --- the retry posture, stated and bounded ----------------------------------


def test_a_rate_limit_that_clears_on_the_retry_produces_a_forecast() -> None:
    adapter, _transport, sleeper = build(
        [HttpResponse(status=429, body=b""), ok(points_body()), ok(forecast_body())]
    )
    assert adapter.forecast_for(VENUE).value is not None
    assert len(sleeper.delays) == 1


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_server_errors_are_retried_once(status: int) -> None:
    adapter, transport, sleeper = build(
        [HttpResponse(status=status, body=b""), HttpResponse(status=status, body=b"")]
    )
    assert adapter.forecast_for(VENUE).absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert len(transport.urls) == 2
    assert sleeper.delays == [RETRY_DELAY_SECONDS]


@pytest.mark.parametrize("status", [400, 403, 404, 410])
def test_other_client_errors_are_not_retried(status: int) -> None:
    """The bound is not "retry until it works": a 403 will not become a 200."""
    adapter, transport, sleeper = build([HttpResponse(status=status, body=b"")])
    assert adapter.forecast_for(VENUE).absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert len(transport.urls) == 1
    assert sleeper.delays == []


# --- answered, but nothing yet ----------------------------------------------


def test_an_empty_period_list_is_not_yet_observed_rather_than_a_failure() -> None:
    """The source answered and the quantity has not accumulated — that reason's
    own definition. Calling this *source unavailable* would assert a failure
    that did not happen."""
    adapter, _, _ = build([ok(points_body()), ok(forecast_body([]))])
    field = adapter.forecast_for(VENUE)
    assert field.value is None
    assert field.absence is AbsenceReason.NOT_YET_OBSERVED
    assert field.source_id == SOURCE_ID


# --- caching, with its bound ------------------------------------------------


def test_a_second_read_on_one_adapter_inside_the_bound_does_not_refetch() -> None:
    """The cache works *within* one adapter's lifetime — and that is all this proves.

    Its previous name claimed a Streamlit rerun did not re-hit the source, which
    this test never crossed: two calls on one instance are same-instance reuse.
    The rerun boundary is a property of who owns the adapter rather than of the
    adapter itself, so it is proven where it lives — at the composition root, in
    ``tests/app/test_parks_page.py``. Test names are claims and get audited like
    any other claim.
    """
    clock = StepClock()
    adapter, transport, _ = build([ok(points_body()), ok(forecast_body())], clock=clock)
    first = adapter.forecast_for(VENUE)
    calls = len(transport.urls)
    clock.advance(FORECAST_FRESHNESS - timedelta(minutes=1))
    second = adapter.forecast_for(VENUE)
    assert len(transport.urls) == calls
    assert second is first


def test_the_cached_value_keeps_the_time_it_was_obtained() -> None:
    """The whole point of putting the timestamp on the value: age survives the
    cache instead of being erased by it."""
    clock = StepClock()
    adapter, _, _ = build([ok(points_body()), ok(forecast_body())], clock=clock)
    adapter.forecast_for(VENUE)
    clock.advance(timedelta(minutes=20))
    later = adapter.forecast_for(VENUE).value
    assert later is not None
    assert later.obtained_at == START  # not the read time, the fetch time


def test_the_bound_expires_and_the_source_is_asked_again() -> None:
    clock = StepClock()
    adapter, transport, _ = build(
        [ok(points_body()), ok(forecast_body()), ok(forecast_body())], clock=clock
    )
    adapter.forecast_for(VENUE)
    calls = len(transport.urls)
    clock.advance(FORECAST_FRESHNESS + timedelta(minutes=1))
    refreshed = adapter.forecast_for(VENUE).value
    assert len(transport.urls) > calls
    assert refreshed is not None
    assert refreshed.obtained_at == clock.moment


def test_the_gridpoint_is_resolved_once_because_ballparks_do_not_move() -> None:
    clock = StepClock()
    adapter, transport, _ = build(
        [ok(points_body()), ok(forecast_body()), ok(forecast_body())], clock=clock
    )
    adapter.forecast_for(VENUE)
    clock.advance(FORECAST_FRESHNESS + timedelta(minutes=1))
    adapter.forecast_for(VENUE)
    assert sum(1 for url in transport.urls if "/points/" in url) == 1


def test_each_venue_is_addressed_by_its_own_coordinates() -> None:
    adapter, transport, _ = build(
        [ok(points_body()), ok(forecast_body()), ok(points_body()), ok(forecast_body())]
    )
    adapter.forecast_for(VENUE)
    adapter.forecast_for(OTHER_VENUE)
    points = [url for url in transport.urls if "/points/" in url]
    assert points == [
        f"https://{NWS_HOST}/points/40.830,-73.926",
        f"https://{NWS_HOST}/points/41.948,-87.655",
    ]


def test_the_freshness_bound_is_stated_in_words_for_the_page() -> None:
    adapter, _, _ = build([])
    assert "30 minutes" in adapter.freshness_statement()


# --- identity and the host pin ----------------------------------------------


def test_every_request_carries_the_identifying_user_agent() -> None:
    adapter, transport, _ = build([ok(points_body()), ok(forecast_body())])
    adapter.forecast_for(VENUE)
    assert transport.headers
    for headers in transport.headers:
        assert headers["User-Agent"] == DEFAULT_CONTACT


def test_the_contact_is_the_repository_url_and_never_an_email_address() -> None:
    """The Product Owner's decision, asserted so it cannot drift: an address
    would be sent to a third party on every request."""
    assert DEFAULT_CONTACT == "https://github.com/jrsandovalxx-beep/greenmachine-next"
    assert "@" not in DEFAULT_CONTACT


def test_every_url_the_adapter_builds_names_the_pinned_host() -> None:
    adapter, transport, _ = build(
        [ok(points_body()), ok(forecast_body()), ok(points_body()), ok(forecast_body())]
    )
    adapter.forecast_for(VENUE)
    adapter.forecast_for(OTHER_VENUE)
    assert transport.urls
    for url in transport.urls:
        assert url.startswith(f"https://{NWS_HOST}/")


def test_a_diagnostic_clears_once_the_source_answers() -> None:
    """A stale reason beside a present value would be its own small lie."""
    clock = StepClock()
    adapter, _, _ = build(
        [
            HttpResponse(status=503, body=b""),
            HttpResponse(status=503, body=b""),
            ok(points_body()),
            ok(forecast_body()),
        ],
        clock=clock,
    )
    adapter.forecast_for(VENUE)
    assert VENUE.venue_id in adapter.diagnostics()
    clock.advance(FORECAST_FRESHNESS + timedelta(minutes=1))
    assert adapter.forecast_for(VENUE).value is not None
    assert VENUE.venue_id not in adapter.diagnostics()
