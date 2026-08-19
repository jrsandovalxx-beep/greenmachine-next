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

from pathlib import Path

import pytest

from greenmachine.weather.transport import (
    NWS_HOST,
    HostNotPermittedError,
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
