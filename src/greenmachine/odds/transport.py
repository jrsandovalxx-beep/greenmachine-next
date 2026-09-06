"""The market-odds network edge: one host, proven (D-187).

The same construction as the MLB and NWS transports (D-069, §GMF-005): the
allowlist is a module constant — ``api.the-odds-api.com`` and no other host —
the refusal happens before a socket exists, and every redirect target is
re-validated against the same rule. The exception family is shared with the
MLB transport so the one retry helper serves both edges. Interpretation
lives in ``greenmachine.odds.client``; this module performs one bounded GET
and reports what happened.

**No test ever exercises the real transport.** The suite-wide socket guard
(GM-008) has no carve-out here either: tests bind a fake and only the
deployed application opens a connection.
"""

from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from urllib.parse import urlparse

from greenmachine.live.transport import (
    HostNotPermittedError,
    HttpResponse,
    Transport,
    TransportTimeoutError,
    TransportTruncatedError,
    TransportUnreachableError,
)

# The only host the market comparison may contact. Not configurable, not a
# parameter, not assembled from parts: a constant, so the pin is a fact
# about the code rather than a property of a caller's argument (D-187).
ODDS_HOST = "api.the-odds-api.com"
ODDS_SCHEME = "https"

# Bounded so a hung connection cannot hang a page render.
REQUEST_TIMEOUT_SECONDS = 10.0

__all__ = [
    "ODDS_HOST",
    "ODDS_SCHEME",
    "REQUEST_TIMEOUT_SECONDS",
    "UrllibTransport",
    "pinned_opener",
    "require_pinned_host",
]


def require_pinned_host(url: str) -> None:
    """Refuse any URL that is not ``https://api.the-odds-api.com/...``.

    Checked before a socket exists, and checked on the parsed host rather
    than by substring: ``https://api.the-odds-api.com.evil.example/`` and
    ``https://user@api.the-odds-api.com@evil.example/`` both fail here,
    which a ``startswith`` test would not catch.
    """
    parsed = urlparse(url)
    if parsed.scheme != ODDS_SCHEME or parsed.hostname != ODDS_HOST:
        raise HostNotPermittedError(
            f"refused {url!r}: this transport reaches {ODDS_SCHEME}://{ODDS_HOST} and "
            "no other host — the pin is a module constant, not a parameter"
        )


class PinnedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Applies the host pin to every redirect target, before it is followed.

    ``redirect_request`` is where the stdlib decides whether and how to
    follow a 3xx. Checking here rather than after the fact means the refused
    hop is never opened, and it keeps one rule in one function: the same
    :func:`require_pinned_host` the caller's URL passes through.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> urllib.request.Request | None:
        require_pinned_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)  # type: ignore[arg-type]


def pinned_opener() -> urllib.request.OpenerDirector:
    """An opener whose redirect handling is the pinned one.

    Built explicitly rather than relying on the module-level default opener,
    because that default is global mutable state any import could have
    changed.
    """
    return urllib.request.build_opener(PinnedRedirectHandler)


class UrllibTransport:
    """The stdlib transport. No third-party HTTP client enters this project."""

    __slots__ = ("_opener", "_timeout")

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout_seconds
        self._opener = pinned_opener()

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        require_pinned_host(url)
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return HttpResponse(status=int(response.status), body=response.read())
        except urllib.error.HTTPError as exc:
            # A status the server actually sent: 404, 429 and 5xx arrive here
            # and are responses, not failures. The caller decides what they
            # mean.
            return HttpResponse(status=int(exc.code), body=exc.read())
        except TimeoutError as exc:
            raise TransportTimeoutError(f"request to {url!r} exceeded {self._timeout}s") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TransportTimeoutError(f"request to {url!r} timed out") from exc
            raise TransportUnreachableError(f"request to {url!r} failed: {exc.reason}") from exc
        except http.client.HTTPException as exc:
            raise TransportTruncatedError(f"request to {url!r} truncated: {exc}") from exc
        except OSError as exc:  # socket-level failures below URLError
            raise TransportUnreachableError(f"request to {url!r} failed: {exc}") from exc

    def __repr__(self) -> str:
        return f"UrllibTransport(host={ODDS_HOST!r}, timeout_seconds={self._timeout})"


# Satisfies the shared protocol at import time (the same assertion the MLB
# transport makes structurally).
_: Transport = UrllibTransport()
