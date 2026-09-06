"""The market comparison (D-187): The Odds API behind a pinned transport."""

from .client import (
    NO_PROPS_REASON,
    MarketRead,
    OddsEvent,
    PayloadMalformedError,
    TheOddsApi,
    market_snapshot,
    normalize_name,
)
from .policy import (
    ET,
    MARKET_ABSENCE_KEEP,
    MARKET_FIRST_CHECK_ET,
    MARKET_PRICED_KEEP,
    MarketMemo,
    in_market_quiet_hours,
    market_keep,
)
from .transport import ODDS_HOST, UrllibTransport, require_pinned_host

__all__ = [
    "ET",
    "MARKET_ABSENCE_KEEP",
    "MARKET_FIRST_CHECK_ET",
    "MARKET_PRICED_KEEP",
    "NO_PROPS_REASON",
    "ODDS_HOST",
    "MarketMemo",
    "MarketRead",
    "OddsEvent",
    "PayloadMalformedError",
    "TheOddsApi",
    "UrllibTransport",
    "in_market_quiet_hours",
    "market_keep",
    "market_snapshot",
    "normalize_name",
    "require_pinned_host",
]
