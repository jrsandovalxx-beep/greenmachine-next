"""The market comparison (D-187): The Odds API behind a pinned transport."""

from .client import (
    MarketRead,
    OddsEvent,
    PayloadMalformedError,
    TheOddsApi,
    market_snapshot,
    normalize_name,
)
from .transport import ODDS_HOST, UrllibTransport, require_pinned_host

__all__ = [
    "ODDS_HOST",
    "MarketRead",
    "OddsEvent",
    "PayloadMalformedError",
    "TheOddsApi",
    "UrllibTransport",
    "market_snapshot",
    "normalize_name",
    "require_pinned_host",
]
