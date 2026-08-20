"""The host pin: §GMF-005's replacement for "no network implementation exists".

Every package until now reported *absence* as D-015/D-017 evidence. This ticket
adds the project's first network path, so absence stops being available and
something stronger takes its place: exactly one implementation, reaching exactly
one host, with every other host refused — **proven here rather than asserted**.

D-057 boundary 1 follows structurally. No MLB host is reachable through this
transport, not because none is mentioned, but because the pin is a module
constant and the refusal happens before a socket exists.
"""

from __future__ import annotations

import email.message
import urllib.request
from pathlib import Path

import pytest

from greenmachine.weather.transport import (
    NWS_HOST,
    HostNotPermittedError,
    PinnedRedirectHandler,
    UrllibTransport,
    require_pinned_host,
)

SRC = Path(__file__).resolve().parents[3] / "src" / "greenmachine"


@pytest.mark.parametrize(
    "url",
    [
        "https://statsapi.mlb.com/api/v1/schedule",
        "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors",
        "https://www.mlb.com/scores",
        "https://api.weather.gov.evil.example/points/1,2",  # lookalike suffix
        "https://evil.example/api.weather.gov/points/1,2",  # host in the path
        "http://api.weather.gov/points/1,2",  # right host, wrong scheme
        "https://user@evil.example/points/1,2",
        "ftp://api.weather.gov/points/1,2",
        "file:///etc/passwd",
        "//api.weather.gov/points/1,2",  # protocol-relative
    ],
)
def test_every_host_but_the_pinned_one_is_refused(url: str) -> None:
    with pytest.raises(HostNotPermittedError):
        require_pinned_host(url)


def test_the_pinned_host_is_allowed() -> None:
    """Anti-vacuity: a refusal that refused everything would prove nothing."""
    require_pinned_host(f"https://{NWS_HOST}/points/40.830,-73.926")


def test_no_mlb_host_can_be_reached_through_the_transport() -> None:
    """D-057 boundary 1, proven by the pin rather than by absence.

    The transport is exercised directly with MLB hosts: it refuses before any
    name resolution, so GM-008's guard is not even the thing that stops it.
    """
    transport = UrllibTransport()
    for url in (
        "https://statsapi.mlb.com/api/v1/teams",
        "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors",
    ):
        with pytest.raises(HostNotPermittedError):
            transport.get(url, {"User-Agent": "test"})


def test_exactly_one_module_in_src_can_open_a_connection() -> None:
    """The enumerated-presence claim, asserted over the whole source tree.

    One network-capable implementation, at a named path. If a second appears,
    this fails and the package's central claim has to be rewritten rather than
    quietly outgrown.
    """
    network_modules = {"urllib", "http", "socket", "ssl", "ftplib", "requests", "httpx", "aiohttp"}
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for module in network_modules:
                if stripped.startswith(f"import {module}") or stripped.startswith(f"from {module}"):
                    offenders.append(f"{path.relative_to(SRC).as_posix()}: {stripped}")
    assert all(entry.startswith("weather/transport.py:") for entry in offenders), offenders
    assert offenders, "the sweep found no network import at all - the walk is broken"


# --- the hop that matters: redirects ----------------------------------------


def _redirect_to(target: str) -> urllib.request.Request | None:
    """Ask the pinned handler to follow a synthetic redirect to ``target``.

    Calls the stdlib's own redirect-decision method directly. No socket opens,
    GM-008 stays armed, and the assertion is about the decision rather than
    about what a server happened to do.
    """
    handler = PinnedRedirectHandler()
    request = urllib.request.Request(
        f"https://{NWS_HOST}/points/40.830,-73.926", headers={"User-Agent": "test"}
    )
    return handler.redirect_request(request, None, 302, "Found", email.message.Message(), target)


@pytest.mark.parametrize(
    "target",
    [
        "https://statsapi.mlb.com/api/v1/teams",
        "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors",
        "https://api.weather.gov.evil.example/points/1,2",
        "http://api.weather.gov/points/1,2",
        "https://evil.example/points/1,2",
    ],
)
def test_a_redirect_off_the_pinned_host_is_refused(target: str) -> None:
    """The defect this replaces: the first request was checked and the hop the
    redirect handler opened was not, so a 302 could carry the request — and the
    identifying User-Agent copied onto it — to any host the source named."""
    with pytest.raises(HostNotPermittedError):
        _redirect_to(target)


def test_a_redirect_that_stays_on_the_pinned_host_is_still_followed() -> None:
    """Re-validation rather than blanket refusal, and this is the difference.

    Refusing every redirect would also be safe and would turn a legitimate NWS
    redirect into thirty unavailable forecasts — discovered on a live deployment
    at submission 2, the most expensive place to learn it.
    """
    followed = _redirect_to(f"https://{NWS_HOST}/gridpoints/ABC/1,2/forecast/hourly")
    assert followed is not None
    assert followed.get_full_url().startswith(f"https://{NWS_HOST}/")


def test_the_transport_installs_the_pinned_redirect_handler() -> None:
    """Anti-vacuity: the handler above only protects requests that actually use
    it, so the transport must build an opener carrying it rather than relying on
    urllib's default opener — which is global mutable state and carries the
    unpinned handler."""
    transport = UrllibTransport()
    handlers = transport._opener.handlers
    assert any(isinstance(handler, PinnedRedirectHandler) for handler in handlers)
