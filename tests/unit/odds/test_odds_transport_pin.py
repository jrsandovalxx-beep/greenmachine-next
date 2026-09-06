"""The odds host pin (D-187): one allowlisted host, everything else refused.

Mirrors the MLB and NWS pin proofs: the allowlist is a module constant,
the refusal happens before a socket exists, and every redirect target is
re-validated — proven here rather than asserted.
"""

from __future__ import annotations

import urllib.request

import pytest

from greenmachine.live.transport import HostNotPermittedError
from greenmachine.odds.transport import (
    ODDS_HOST,
    PinnedRedirectHandler,
    UrllibTransport,
    require_pinned_host,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://statsapi.mlb.com/api",  # the other transports' host
        "https://api.the-odds-api.com.evil.example/v4",  # lookalike suffix
        "https://evil.example/api.the-odds-api.com/v4",  # host in the path
        "http://api.the-odds-api.com/v4/sports",  # right host, wrong scheme
        "https://user@api.the-odds-api.com.evil.example/v4",
        "ftp://api.the-odds-api.com/v4",
        "file:///etc/passwd",
        "//api.the-odds-api.com/v4/sports",  # protocol-relative
    ],
)
def test_every_host_but_the_allowlisted_one_is_refused(url: str) -> None:
    with pytest.raises(HostNotPermittedError):
        require_pinned_host(url)


def test_the_allowlisted_host_is_allowed() -> None:
    """Anti-vacuity: a refusal that refused everything would prove nothing."""
    require_pinned_host(f"https://{ODDS_HOST}/v4/sports")


def test_the_transport_refuses_before_a_socket_exists() -> None:
    transport = UrllibTransport()
    with pytest.raises(HostNotPermittedError):
        transport.get("https://evil.example/api", {"User-Agent": "test"})


def test_a_redirect_off_host_is_refused() -> None:
    handler = PinnedRedirectHandler()
    request = urllib.request.Request(f"https://{ODDS_HOST}/v4/sports")
    with pytest.raises(HostNotPermittedError):
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/x")
