"""The one network-capable implementation in this repository (§GMF-005).

Every byte this project fetches passes through :class:`UrllibTransport`, and
that class can reach exactly one host. The pin is a module constant and the
refusal is exercised by test, so "no MLB host is reachable by any code path"
is proven by construction rather than asserted from absence — which is what
D-057 boundary 1 needs once a live path exists at all.

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

    Raised before any network operation. This is the mechanism behind the
    package's central claim: the transport cannot be pointed somewhere else,
    so no MLB host — or any other — is reachable through it.
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


class UrllibTransport:
    """The stdlib transport. No third-party HTTP client enters this project."""

    __slots__ = ("_timeout",)

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout_seconds

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        require_pinned_host(url)
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
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
        return f"UrllibTransport(timeout_seconds={self._timeout})"


def real_sleep(seconds: float) -> None:
    """The production delay. Injected, so no test ever waits (§GMF-005)."""
    time.sleep(seconds)
