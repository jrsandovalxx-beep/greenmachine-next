"""The Odds API client: batter home-run props for one slate (D-187).

Build-order item 6 (PO): the market comparison. The source publishes each
batter's "1+ home runs" prop as a two-way Over/Under 0.5 market per
bookmaker; the market read is the de-vigged Over — the fair chance the
books collectively price — on the same percent scale as the D-186
calibrated curve, so the shortlist can sit the two numbers side by side.
A batter no book priced, a slate whose props have not posted, and an
unreachable or unpaid key all read as named absences, never invented
numbers.

Reads are aggregated per player across the books that priced him; the
``books`` count says how wide the agreement base is. Player identity from
the feed is a display name, so matching to the slate's batters is by
normalized name — the same letters-only fold the season-board joins use.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from greenmachine.live.mlb_api import FetchFailure
from greenmachine.live.transport import Transport, TransportError, get_with_retry

from .transport import ODDS_HOST

_HEADERS = {"User-Agent": "greenmachine-next/1.0 (private research dashboard)"}
_BASE = f"https://{ODDS_HOST}/v4/sports/baseball_mlb"
_SLATE_ZONE = ZoneInfo("America/Phoenix")

# The market key for the "1+ home runs" prop, and the line the mainstream
# books post it at. Anything off 0.5 is an alternate ladder rung, not the
# headline price.
_HR_MARKET = "batter_home_runs"
_HR_POINT = Decimal("0.5")

# The empty-slate absence, named once so the app can tell "nothing posted
# yet" apart from a transport failure (D-189) — and so the unit pin matches
# the same constant rather than a second copy of the sentence.
NO_PROPS_REASON = "no batter home-run props posted for this slate"


class PayloadMalformedError(Exception):
    """The odds feed answered but not in the published shape."""


@dataclass(frozen=True)
class OddsEvent:
    """One listed fixture: the feed's id for it, its slate-day teams, and
    the first-pitch instant (D-190) — the freshness policy gates the paid
    props sweep on it, and the events list itself is free."""

    event_id: str
    home_team: str
    away_team: str
    commence_time: datetime


@dataclass(frozen=True)
class MarketRead:
    """One batter's market read: the de-vigged fair chance (percent scale,
    matching the D-186 curve) and the number of books that priced his
    two-way market."""

    fair_percent: Decimal
    books: int


def normalize_name(name: str) -> str:
    """The join key for feed-name ↔ slate-name: lowercase letters only.

    Accents fold (NFKD), punctuation and spaces drop — "José Ramírez" and
    "Jose Ramirez" land on the same key. Collisions across one slate are
    vanishingly rare and would read as the same market line, never a crash.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if c.isascii() and c.isalpha()).lower()


def _parse_json(body: bytes, context: str) -> Any:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadMalformedError(f"{context}: body is not UTF-8") from exc
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadMalformedError(f"{context}: body is not JSON") from exc
    return parsed


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise PayloadMalformedError(f"{context}: expected an array")
    return value


def _require_str(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise PayloadMalformedError(f"{context}: expected a non-empty string")
    return value


def _decimal_price(value: Any, context: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PayloadMalformedError(f"{context}: expected a numeric price, got {value!r}")
    price = Decimal(str(value))
    if not price.is_finite() or price <= 1:
        raise PayloadMalformedError(f"{context}: price {value!r} is not a valid decimal odd")
    return price


def _devig_over(over: Decimal, under: Decimal) -> Decimal:
    """The fair Over probability with the book's margin stripped: each side's
    implied share normalized against their sum."""
    implied_over = 1 / over
    return implied_over / (implied_over + 1 / under)


class TheOddsApi:
    """Reads The Odds API through an injected, host-pinned transport."""

    __slots__ = ("_api_key", "_transport")

    def __init__(self, transport: Transport, api_key: str) -> None:
        self._transport = transport
        self._api_key = api_key

    def _get_json(self, path: str, context: str) -> Any | FetchFailure:
        # The key travels only in the request URL, never in a reason string.
        url = f"{_BASE}{path}{'&' if '?' in path else '?'}apiKey={self._api_key}"
        try:
            response = get_with_retry(self._transport, url, _HEADERS)
        except TransportError as exc:
            return FetchFailure(f"{context}: transport failed ({type(exc).__name__})")
        if response.status != 200:
            return FetchFailure(f"{context}: HTTP {response.status}")
        try:
            return _parse_json(response.body, context)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))

    def fetch_events(self, day: date) -> tuple[OddsEvent, ...] | FetchFailure:
        """The fixtures commencing on the slate day (Phoenix date, like the
        board's own "today"), as the feed's event ids for the props call."""
        parsed = self._get_json("/events?dateFormat=iso", "events list")
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            rows = _require_list(parsed, "events list")
            events: list[OddsEvent] = []
            for row in rows:
                if not isinstance(row, dict):
                    raise PayloadMalformedError("events list: expected objects")
                event_id = _require_str(row.get("id"), "events list")
                commence = _require_str(row.get("commence_time"), "events list")
                home = _require_str(row.get("home_team"), "events list")
                away = _require_str(row.get("away_team"), "events list")
                local = datetime.fromisoformat(commence.replace("Z", "+00:00")).astimezone(
                    _SLATE_ZONE
                )
                if local.date() == day:
                    events.append(
                        OddsEvent(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            commence_time=datetime.fromisoformat(commence.replace("Z", "+00:00")),
                        )
                    )
        except (PayloadMalformedError, ValueError) as exc:
            return FetchFailure(f"events list: {exc}")
        return tuple(events)

    def fetch_hr_props(self, event_id: str) -> tuple[tuple[str, str, Decimal], ...] | FetchFailure:
        """(normalized player, book key, fair Over 0.5 HR probability) for
        every book that priced the two-way market on this fixture. A book
        posting only one side, or a ladder without the 0.5 rung, simply has
        no read here."""
        context = f"home-run props for event {event_id}"
        parsed = self._get_json(
            f"/events/{event_id}/odds?regions=us&markets={_HR_MARKET}&oddsFormat=decimal",
            context,
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            if not isinstance(parsed, dict):
                raise PayloadMalformedError(f"{context}: expected an object")
            bookmakers = _require_list(parsed.get("bookmakers", []), context)
            reads: list[tuple[str, str, Decimal]] = []
            for book in bookmakers:
                if not isinstance(book, dict):
                    raise PayloadMalformedError(f"{context}: expected bookmaker objects")
                book_key = _require_str(book.get("key"), context)
                for market in _require_list(book.get("markets", []), context):
                    if not isinstance(market, dict) or market.get("key") != _HR_MARKET:
                        continue
                    reads.extend(_read_market(market, book_key, context))
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return tuple(reads)


def _read_market(
    market: dict[str, Any], book_key: str, context: str
) -> list[tuple[str, str, Decimal]]:
    """The de-vigged reads from one book's home-run market."""
    outcomes = _require_list(market.get("outcomes", []), context)
    by_player: dict[str, dict[str, Decimal]] = {}
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            raise PayloadMalformedError(f"{context}: expected outcome objects")
        player = outcome.get("description")
        side = outcome.get("name")
        point = outcome.get("point")
        if not isinstance(player, str) or not player or side not in ("Over", "Under"):
            continue
        if point is None or Decimal(str(point)) != _HR_POINT:
            continue  # an alternate ladder rung, not the headline 0.5
        price = _decimal_price(outcome.get("price"), context)
        by_player.setdefault(normalize_name(player), {})[side] = price
    reads = []
    for player, sides in by_player.items():
        over = sides.get("Over")
        under = sides.get("Under")
        if over is not None and under is not None:
            reads.append((player, book_key, _devig_over(over, under)))
    return reads


def market_snapshot(api: TheOddsApi, day: date) -> dict[str, MarketRead] | FetchFailure:
    """The slate's market reads keyed by normalized batter name.

    Each fixture's props are one request; a fixture that fails degrades out
    of the average rather than failing the slate, and a slate with no
    priced batter at all is a named absence — props post through the day,
    so an empty morning board is a timing fact, not an error.
    """
    events = api.fetch_events(day)
    if isinstance(events, FetchFailure):
        return events
    fairs: dict[str, list[Decimal]] = {}
    books: dict[str, set[str]] = {}
    for event in events:
        props = api.fetch_hr_props(event.event_id)
        if isinstance(props, FetchFailure):
            continue
        for player, book_key, fair in props:
            fairs.setdefault(player, []).append(fair)
            books.setdefault(player, set()).add(book_key)
    if not fairs:
        return FetchFailure(NO_PROPS_REASON)
    snapshot: dict[str, MarketRead] = {}
    for player, prices in fairs.items():
        mean = sum(prices) / Decimal(len(prices))
        snapshot[player] = MarketRead(
            fair_percent=(mean * 100).quantize(Decimal("0.0001")),
            books=len(books[player]),
        )
    return snapshot
