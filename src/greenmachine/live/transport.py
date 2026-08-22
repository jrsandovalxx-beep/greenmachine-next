"""The MLB network edge: every MLB byte enters through here (§GMF-006, D-069).

D-069 authorizes automated pulls from exactly two hosts —
``statsapi.mlb.com`` and ``baseballsavant.mlb.com`` — under the discipline
the weather ticket established for ``api.weather.gov``. This module is that
discipline
for the MLB hosts: the allowlist is a module constant, not a parameter, and
the refusal happens before a socket exists — on the caller's URL, and again
on every redirect target via :class:`PinnedRedirectHandler`, so no hop this
transport makes can name a host outside the allowlist.

The transport deliberately knows nothing about baseball: it performs bounded
GETs and reports what happened. Interpretation — which failures mean *source
unavailable*, what a slate or a leaderboard is — belongs to
``greenmachine.live.mlb_api`` and ``greenmachine.live.savant``.

**No test ever exercises the real transport.** The suite-wide guard
(``tests/unit/golden/test_network_blocking.py``) blocks every socket entry
point with no carve-out, and nothing here asks for one: adapters take a
``Transport``, tests bind fakes, and the only thing that ever opens a
connection is the deployed application's composition root.
"""

from __future__ import annotations

import http.client
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

# The only hosts this transport may contact (D-069(a)). Not configurable, not
# a parameter, not assembled from parts: a constant, so the allowlist is a
# fact about the code rather than a property of a caller's argument. The NWS
# host has its own transport and pin in greenmachine.weather.transport.
MLB_HOSTS: frozenset[str] = frozenset({"statsapi.mlb.com", "baseballsavant.mlb.com"})
MLB_SCHEME = "https"

# Bounded so a hung connection cannot hang a page render. Generous relative to
# the weather pin because Savant per-event CSVs run to a few megabytes.
REQUEST_TIMEOUT_SECONDS = 30.0

# Retry posture (D-069(a), "bounded"): transient statuses get exactly one
# retry after a fixed delay; everything else answers as it arrived. The delay
# is injected at the call site so no test ever waits.
RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2.0


class TransportError(Exception):
    """Base for every way a request can fail to produce a response."""


class TransportTimeoutError(TransportError):
    """The request exceeded its bound without answering."""


class TransportUnreachableError(TransportError):
    """The host could not be reached: DNS, connection or protocol failure."""


class TransportTruncatedError(TransportError):
    """The response body was cut short mid-read — a transient break on a
    multi-megabyte payload, not a statement about the source's availability."""


class HostNotPermittedError(TransportError):
    """A URL was refused because it names a host outside the allowlist.

    Raised before the hop it refuses is opened — on the caller's URL, and
    again on any redirect target. Together those two checkpoints are the
    mechanism behind the package's claim: no hop this transport makes can
    name a host outside ``MLB_HOSTS``.
    """


@dataclass(frozen=True)
class HttpResponse:
    """What the transport observed: a status and a body, nothing interpreted."""

    status: int
    body: bytes


class Transport(Protocol):
    """One bounded GET. Implementations answer, or raise ``TransportError``."""

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        """Fetch ``url``; return the response, or raise a ``TransportError``."""
        ...


def require_permitted_host(url: str) -> None:
    """Refuse any URL that is not ``https://`` an allowlisted MLB host.

    Checked before a socket exists, and checked on the parsed host rather than
    by substring: ``https://statsapi.mlb.com.evil.example/`` and
    ``https://user@statsapi.mlb.com@evil.example/`` both fail here, which a
    ``startswith`` test would not catch.
    """
    parsed = urlparse(url)
    if parsed.scheme != MLB_SCHEME or parsed.hostname not in MLB_HOSTS:
        raise HostNotPermittedError(
            f"refused {url!r}: this transport reaches only {sorted(MLB_HOSTS)} over "
            f"{MLB_SCHEME} — the allowlist is a module constant, not a parameter"
        )


class PinnedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Applies the host allowlist to every redirect target, before it is followed.

    ``redirect_request`` is where the stdlib decides whether and how to follow
    a 3xx. Checking here rather than after the fact means the refused hop is
    never opened, and it keeps one rule in one function: the same
    :func:`require_permitted_host` the caller's URL passes through.
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
        require_permitted_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)  # type: ignore[arg-type]


def pinned_opener() -> urllib.request.OpenerDirector:
    """An opener whose redirect handling is the pinned one.

    Built explicitly rather than relying on the module-level default opener,
    because that default is global mutable state any import could have changed.
    """
    return urllib.request.build_opener(PinnedRedirectHandler)


class UrllibTransport:
    """The stdlib transport. No third-party HTTP client enters this project."""

    __slots__ = ("_opener", "_timeout")

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout_seconds
        self._opener = pinned_opener()

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        require_permitted_host(url)
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return HttpResponse(status=int(response.status), body=response.read())
        except urllib.error.HTTPError as exc:
            # A status the server actually sent: 404, 429 and 5xx arrive here and
            # are responses, not failures. The caller decides what they mean.
            return HttpResponse(status=int(exc.code), body=exc.read())
        except TimeoutError as exc:
            raise TransportTimeoutError(f"request to {url!r} exceeded {self._timeout}s") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TransportTimeoutError(f"request to {url!r} timed out") from exc
            raise TransportUnreachableError(f"request to {url!r} failed: {exc.reason}") from exc
        except http.client.HTTPException as exc:
            # IncompleteRead, RemoteDisconnected: the body died in flight.
            raise TransportTruncatedError(f"request to {url!r} truncated: {exc}") from exc
        except OSError as exc:  # socket-level failures below URLError
            raise TransportUnreachableError(f"request to {url!r} failed: {exc}") from exc

    def __repr__(self) -> str:
        return f"UrllibTransport(hosts={sorted(MLB_HOSTS)!r}, timeout_seconds={self._timeout})"


def real_sleep(seconds: float) -> None:
    """The production delay. Injected everywhere, so no test ever waits."""
    time.sleep(seconds)


def get_with_retry(
    transport: Transport,
    url: str,
    headers: dict[str, str],
    sleep: Callable[[float], None] = real_sleep,
) -> HttpResponse:
    """One GET with the bounded retry posture applied to transient statuses.

    The first answer stands unless its status is in ``RETRYABLE_STATUSES`` or
    the body was truncated mid-read, in which case exactly one more attempt
    follows after ``RETRY_DELAY_SECONDS``. Other transport errors are not
    retried here — a timeout or unreachable host is the adapter's *source
    unavailable*, and doubling its latency helps nobody (D-100).
    """
    try:
        response = transport.get(url, headers)
    except TransportTruncatedError:
        # One more attempt: a severed body is transient by nature, and the
        # alternative — dropping the whole day's pitch record — reads as
        # choppy windows downstream (D-100).
        sleep(RETRY_DELAY_SECONDS)
        response = transport.get(url, headers)
    if response.status in RETRYABLE_STATUSES:
        sleep(RETRY_DELAY_SECONDS)
        response = transport.get(url, headers)
    return response
