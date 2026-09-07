"""The market comparison (D-187): The Odds API behind a pinned transport."""

from .client import (
    NO_PROPS_REASON,
    MarketBoard,
    MarketRead,
    OddsEvent,
    PayloadMalformedError,
    TheOddsApi,
    event_reads,
    normalize_name,
)
from .policy import (
    MARKET_ABSENCE_KEEP,
    MARKET_CLOSE_GRACE,
    MARKET_PRICED_KEEP,
    MARKET_SWEEP_LEAD,
    MarketMemo,
    event_phase,
    market_keep,
)
from .transport import ODDS_HOST, UrllibTransport, require_pinned_host

__all__ = [
    "MARKET_ABSENCE_KEEP",
    "MARKET_CLOSE_GRACE",
    "MARKET_PRICED_KEEP",
    "MARKET_SWEEP_LEAD",
    "NO_PROPS_REASON",
    "ODDS_HOST",
    "MarketBoard",
    "MarketMemo",
    "MarketRead",
    "OddsEvent",
    "PayloadMalformedError",
    "TheOddsApi",
    "UrllibTransport",
    "event_phase",
    "event_reads",
    "market_keep",
    "normalize_name",
    "require_pinned_host",
]
