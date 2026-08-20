"""The live NWS adapter behind the §GMF-004 seam (§GMF-005 submission 1).

Everything uncertain about the outside world is decided here, and decided in one
place: which failures mean *source unavailable*, when a retry is warranted, how
long an answer stays fresh, and what a reader is told when no number can be
shown. The network edge itself is ``greenmachine.weather.transport``, which can
reach exactly one host.

**Failure is designed, not caught.** D-054 records NWS as open data with no key,
unpublished rate limits, and over-limit requests retryable within a few seconds.
Against that, each named failure maps to an absence the screens already render:

- timeout, connection failure, non-200 (404 included), malformed payload, a
  rate limit that survives the one permitted retry, and a redirect the host pin
  refuses: ``SOURCE_UNAVAILABLE``;
- answered, with no period for this venue yet: ``NOT_YET_OBSERVED``.

That last row is not a failure at all, and it is why the vocabulary needs no new
member: the source answered and the quantity has not accumulated, which is that
reason's own definition. ``NOT_APPLICABLE`` is structural — a venue with no roof
to observe — and this adapter never emits it.

``SOURCE_UNAVAILABLE`` covers both "timed out" and "outside coverage", which are
identical in the contract and very different to a person. Rather than split the
enum, the adapter records a plain-language reason per venue in
:meth:`diagnostics`, which the composition root renders beneath the table: the
additive-remedy pattern this project has used since GMF-002, with the cell
representation untouched.

**Caching, with the bound stated to the reader.** A Streamlit page reruns on
every interaction, so without a cache one density click would be thirty
requests. Two bounds for two kinds of fact: a venue's gridpoint is cached for
the session because ballparks do not move, and a forecast for
``FORECAST_FRESHNESS`` because NWS updates roughly hourly. Absences are cached
under the same bound as values — a venue outside coverage answers 404 every
time, and hammering a source to relearn a permanent fact is not diligence. Every
cached value carries the ``obtained_at`` it was fetched with, so age survives the
cache instead of being erased by it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from greenmachine.common.clock import Clock
from greenmachine.inputs.contract import (
    AbsenceReason,
    ParkVenue,
    SnapshotField,
    SourceKind,
    SourceRecord,
    WeatherForecast,
)
from greenmachine.weather.transport import (
    NWS_HOST,
    NWS_SCHEME,
    HostNotPermittedError,
    HttpResponse,
    Transport,
    TransportError,
    TransportTimeoutError,
)

SOURCE_ID = "nws-weather"

# The Product Owner's decided contact value. NWS asks callers to identify
# themselves; this is the repository URL and deliberately not an email address.
# It is configuration rather than a secret — it grants no access, authenticates
# nothing, and is transmitted in cleartext to every recipient by design — so
# D-056's deferral of ``st.secrets`` is untouched: that deferral's trigger is a
# *credentialed* provider, and D-054 records NWS as requiring no key.
DEFAULT_CONTACT = "https://github.com/jrsandovalxx-beep/greenmachine-next"

CONTACT_ENV_VAR = "GM_NWS_CONTACT"

# The stated freshness bound. Named here, printed on the page: a bound that
# lives only in code says nothing to the reader it exists for.
FORECAST_FRESHNESS = timedelta(minutes=30)

# Bounded retry, per D-054's "retryable typically within ~5 seconds". One retry,
# one delay, no ladder, no loop.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
RETRY_DELAY_SECONDS = 5.0
MAX_ATTEMPTS = 2

SOURCE = SourceRecord(
    source_id=SOURCE_ID,
    kind=SourceKind.LIVE_ADAPTER,
    description=(
        "National Weather Service api.weather.gov - open data, requiring no "
        "credential per decision D-054; one host, pinned by module constant; "
        "identifying User-Agent carries the repository URL and no personal address"
    ),
)


class MalformedPayloadError(Exception):
    """The source answered with something this adapter cannot read."""


class StatusFailureError(Exception):
    """A status the source actually sent, carried with its plain meaning."""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"{status} from {url}")
        self.status = status

    def reason(self) -> str:
        if self.status == 404:
            return (
                "this venue is outside the coverage area - NWS forecasts the United "
                "States only (D-055), so the source answered honestly rather than failing"
            )
        if self.status == 429:
            return "the source rate-limited the request, and the one permitted retry also did"
        return f"the source answered {self.status}"


def _as_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MalformedPayloadError(f"{field_name} is not a non-empty string")
    return value


def _as_decimal(value: object, field_name: str) -> Decimal:
    """A number from JSON, via ``str`` so no float ever reaches ``Decimal``."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise MalformedPayloadError(f"{field_name} is not numeric")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:  # pragma: no cover - str() of a number parses
        raise MalformedPayloadError(f"{field_name} is not a parsable number") from exc


def _leading_number(text: str, field_name: str) -> Decimal:
    """NWS reports wind as ``10 mph`` or ``5 to 10 mph``; take the first number."""
    head = text.strip().split()
    if not head:
        raise MalformedPayloadError(f"{field_name} is empty")
    try:
        return Decimal(head[0])
    except InvalidOperation as exc:
        raise MalformedPayloadError(f"{field_name} does not begin with a number") from exc


def _properties(response: HttpResponse, what: str) -> dict[str, Any]:
    try:
        parsed: Any = json.loads(response.body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise MalformedPayloadError(f"{what} is not JSON") from exc
    if not isinstance(parsed, dict):
        raise MalformedPayloadError(f"{what} is not a JSON object")
    properties = parsed.get("properties")
    if not isinstance(properties, dict):
        raise MalformedPayloadError(f"{what} has no properties object")
    return properties


class NwsWeatherAdapter:
    """A ``WeatherAdapter`` whose answers come from api.weather.gov.

    Every collaborator is injected — transport, clock, delay — so the suite
    proves this class without a socket and GM-008 stays armed with no carve-out.
    """

    def __init__(
        self,
        transport: Transport,
        clock: Clock,
        sleep: Callable[[float], None],
        contact: str = DEFAULT_CONTACT,
        freshness: timedelta = FORECAST_FRESHNESS,
    ) -> None:
        self._transport = transport
        self._clock = clock
        self._sleep = sleep
        self._contact = contact
        self._freshness = freshness
        self._gridpoints: dict[str, str] = {}
        self._forecasts: dict[str, tuple[datetime, SnapshotField[WeatherForecast]]] = {}
        self._reasons: dict[str, str] = {}

    # -- the seam's surface -------------------------------------------------

    def forecast_for(self, venue: ParkVenue) -> SnapshotField[WeatherForecast]:
        """A forecast for ``venue``, or an absence carrying its reason."""
        cached = self._forecasts.get(venue.venue_id)
        if cached is not None:
            stored_at, field = cached
            if self._clock.now() - stored_at < self._freshness:
                return field
        field = self._fetch(venue)
        self._forecasts[venue.venue_id] = (self._clock.now(), field)
        return field

    def diagnostics(self) -> dict[str, str]:
        """Per venue, why no number could be shown — in plain language.

        Where ``SOURCE_UNAVAILABLE``'s two very different meanings stay
        distinguishable without a new absence reason: "outside the coverage
        area" is a fact about the ballpark, "the request timed out" a fact about
        the source, and a reader deserves to know which one they are looking at.
        """
        return dict(self._reasons)

    def freshness_statement(self) -> str:
        """The cache bound, in the words the page prints."""
        minutes = int(self._freshness.total_seconds() // 60)
        return f"Live forecasts are re-fetched at most every {minutes} minutes."

    # -- internals ----------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._contact, "Accept": "application/geo+json"}

    def _get(self, url: str) -> HttpResponse:
        """One bounded GET with at most one retry (D-054)."""
        attempt = 1
        while True:
            response = self._transport.get(url, self._headers())
            if response.status not in RETRY_STATUSES or attempt >= MAX_ATTEMPTS:
                return response
            attempt += 1
            self._sleep(RETRY_DELAY_SECONDS)

    def _forecast_url(self, venue: ParkVenue) -> str:
        """Resolve the venue's gridpoint forecast URL, cached for the session."""
        cached = self._gridpoints.get(venue.venue_id)
        if cached is not None:
            return cached
        points = f"{NWS_SCHEME}://{NWS_HOST}/points/{venue.latitude},{venue.longitude}"
        response = self._get(points)
        if response.status != 200:
            raise StatusFailureError(response.status, points)
        properties = _properties(response, "points response")
        url = _as_text(properties.get("forecastHourly"), "properties.forecastHourly")
        self._gridpoints[venue.venue_id] = url
        return url

    def _fetch(self, venue: ParkVenue) -> SnapshotField[WeatherForecast]:
        try:
            url = self._forecast_url(venue)
            response = self._get(url)
            if response.status != 200:
                raise StatusFailureError(response.status, url)
            properties = _properties(response, "forecast response")
            periods = properties.get("periods")
            if not isinstance(periods, list):
                raise MalformedPayloadError("forecast response has no periods list")
            if not periods:
                # The source answered and has nothing for this venue yet: the
                # definition of NOT_YET_OBSERVED, and not a failure.
                self._reasons[venue.venue_id] = (
                    "the forecast answered with no period covering this venue yet"
                )
                return SnapshotField[WeatherForecast].absent(
                    AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID
                )
            period = periods[0]
            if not isinstance(period, dict):
                raise MalformedPayloadError("forecast period is not an object")
            forecast = WeatherForecast(
                temperature_f=_as_decimal(period.get("temperature"), "temperature"),
                wind_speed_mph=_leading_number(
                    _as_text(period.get("windSpeed"), "windSpeed"), "windSpeed"
                ),
                wind_direction=_as_text(period.get("windDirection"), "windDirection"),
                short_forecast=_as_text(period.get("shortForecast"), "shortForecast"),
                obtained_at=self._clock.now(),
            )
        except StatusFailureError as failure:
            self._reasons[venue.venue_id] = failure.reason()
            return SnapshotField[WeatherForecast].absent(
                AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
            )
        except HostNotPermittedError:
            # A hop tried to leave the pinned host. Reported as unavailable like
            # any other non-answer, but named precisely: this is the boundary
            # holding, not the source failing.
            self._reasons[venue.venue_id] = (
                "the source tried to redirect this request off api.weather.gov, and the "
                "host pin refused the hop - no forecast rather than a fetch from elsewhere"
            )
            return SnapshotField[WeatherForecast].absent(
                AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
            )
        except TransportTimeoutError:
            self._reasons[venue.venue_id] = "the request timed out before the source answered"
            return SnapshotField[WeatherForecast].absent(
                AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
            )
        except TransportError as exc:
            self._reasons[venue.venue_id] = (
                f"the source could not be reached ({type(exc).__name__})"
            )
            return SnapshotField[WeatherForecast].absent(
                AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
            )
        except MalformedPayloadError as exc:
            self._reasons[venue.venue_id] = f"the source answered an unreadable payload ({exc})"
            return SnapshotField[WeatherForecast].absent(
                AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID
            )
        self._reasons.pop(venue.venue_id, None)
        return SnapshotField.present(forecast, SOURCE_ID)

    def __repr__(self) -> str:
        return f"NwsWeatherAdapter(host={NWS_HOST!r}, freshness={self._freshness})"
