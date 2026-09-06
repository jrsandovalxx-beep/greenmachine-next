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
    MARKET_ABSENCE_KEEP,
    MARKET_PRE_GAME,
    MARKET_PRICED_KEEP,
    MarketMemo,
    market_keep,
)
from .transport import ODDS_HOST, UrllibTransport, require_pinned_host

__all__ = [
    "MARKET_ABSENCE_KEEP",
    "MARKET_PRE_GAME",
    "MARKET_PRICED_KEEP",
    "NO_PROPS_REASON",
    "ODDS_HOST",
    "MarketMemo",
    "MarketRead",
    "OddsEvent",
    "PayloadMalformedError",
    "TheOddsApi",
    "UrllibTransport",
    "market_keep",
    "market_snapshot",
    "normalize_name",
    "require_pinned_host",
]
