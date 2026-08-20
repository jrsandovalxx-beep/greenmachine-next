"""The one network-capable implementation in this repository (§GMF-005).

Every byte this project fetches passes through :class:`UrllibTransport`, and
**every hop it makes** is constrained to one host. The pin is a module constant
and the refusals are exercised by test, so "no MLB host is reachable by any code
path" is proven by construction rather than asserted from absence — which is
what D-057 boundary 1 needs once a live path exists at all.

**Hops, not just the first request.** An earlier revision validated the URL it
was handed and then passed the request to the default opener, whose
``HTTPRedirectHandler`` answers a 3xx by building a request for the ``Location``
target and opening it — without returning through the check. The pin was
therefore on the one hop that could not go anywhere unexpected, and absent from
the one that could; worse, the redirect handler copies the original headers onto
the new request, so the identifying ``User-Agent`` would have travelled to
whatever host the redirect named. :class:`PinnedRedirectHandler` closes that by
re-validating every redirect target against the same rule.

Re-validation rather than blanket refusal is deliberate. Refusing all redirects
would also be safe, but if NWS legitimately redirects any path in use, every
forecast becomes *source unavailable* — and that would surface on a live
deployment at submission 2, the most expensive place to learn it. Re-validating
keeps the boundary exactly as tight while surviving a legitimate redirect.

The transport deliberately knows nothing about weather: it performs one bounded
GET and reports what happened. Interpretation — which failures mean *source
unavailable*, when a retry is warranted, what a forecast is — belongs to
``greenmachine.weather.nws``, so the network edge stays small enough to read in
one sitting and the logic above it stays testable without a socket.

**No test ever exercises the real transport.** GM-008's suite-wide guard blocks
every socket entry point, with no carve-out for this module, and nothing here
asks for one: the adapter takes a ``Transport``, so tests bind a fake and the
only thing that ever opens a connection is the deployed application.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

# The only host this repository may contact. Not configurable, not a parameter,
# not assembled from parts: a constant, so the pin is a fact about the code
# rather than a property of a caller's argument.
NWS_HOST = "api.weather.gov"
NWS_SCHEME = "https"

# Bounded so a hung connection cannot hang a page render.
REQUEST_TIMEOUT_SECONDS = 10.0


class TransportError(Exception):
    """Base for every way a request can fail to produce a response."""


class TransportTimeoutError(TransportError):
    """The request exceeded its bound without answering."""


class TransportUnreachableError(TransportError):
    """The host could not be reached: DNS, connection or protocol failure."""


class HostNotPermittedError(TransportError):
    """A URL was refused because it does not name the pinned host.

    Raised before the hop it refuses is opened — on the caller's URL, and again
    on any redirect target. Together those two checkpoints are the mechanism
    behind the package's claim: no hop this transport makes can name a host
    other than the pinned one, so no MLB host is reachable through it.
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


def require_pinned_host(url: str) -> None:
    """Refuse any URL that is not ``https://api.weather.gov/...``.

    Checked before a socket exists, and checked on the parsed host rather than
    by substring: ``https://api.weather.gov.example.com/`` and
    ``https://user@api.weather.gov@evil.example/`` both fail here, which a
    ``startswith`` test would not catch.
    """
    parsed = urlparse(url)
    if parsed.scheme != NWS_SCHEME or parsed.hostname != NWS_HOST:
        raise HostNotPermittedError(
            f"refused {url!r}: this transport reaches {NWS_SCHEME}://{NWS_HOST} and "
            "no other host — the pin is a module constant, not a parameter"
        )


class PinnedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Applies the host pin to every redirect target, before it is followed.

    ``redirect_request`` is where the stdlib decides whether and how to follow a
    3xx. Checking here rather than after the fact means the refused hop is never
    opened, and it keeps one rule in one function: the same
    :func:`require_pinned_host` the caller's URL passes through.

    It is an ordinary object with an ordinary method, which is why the guarantee
    is testable without a socket — a test calls this method directly with a
    synthetic ``Location`` and asserts the refusal.
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
        require_pinned_host(url)
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return HttpResponse(status=int(response.status), body=response.read())
        except urllib.error.HTTPError as exc:
            # A status the server actually sent: 404, 429 and 5xx arrive here and
            # are responses, not failures. The adapter decides what they mean.
            return HttpResponse(status=int(exc.code), body=exc.read())
        except TimeoutError as exc:
            raise TransportTimeoutError(f"request to {url!r} exceeded {self._timeout}s") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TransportTimeoutError(f"request to {url!r} timed out") from exc
            raise TransportUnreachableError(f"request to {url!r} failed: {exc.reason}") from exc
        except OSError as exc:  # socket-level failures below URLError
            raise TransportUnreachableError(f"request to {url!r} failed: {exc}") from exc

    def __repr__(self) -> str:
        return f"UrllibTransport(host={NWS_HOST!r}, timeout_seconds={self._timeout})"


def real_sleep(seconds: float) -> None:
    """The production delay. Injected, so no test ever waits (§GMF-005)."""
    time.sleep(seconds)
