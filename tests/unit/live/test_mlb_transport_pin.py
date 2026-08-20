"""The MLB host pin (D-069): two allowlisted hosts, everything else refused.

Mirrors the weather transport's pin proof: the allowlist is a module
constant, the refusal happens before a socket exists, and every redirect
target is re-validated — proven here rather than asserted.
"""

from __future__ import annotations

import email.message
import urllib.request

import pytest

from greenmachine.live.transport import (
    MLB_HOSTS,
    HostNotPermittedError,
    HttpResponse,
    PinnedRedirectHandler,
    UrllibTransport,
    get_with_retry,
    require_permitted_host,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.weather.gov/points/1,2",  # the other transport's host
        "https://statsapi.mlb.com.evil.example/api",  # lookalike suffix
        "https://evil.example/statsapi.mlb.com/api",  # host in the path
        "http://statsapi.mlb.com/api/v1/schedule",  # right host, wrong scheme
        "https://user@statsapi.mlb.com.evil.example/api",
        "ftp://baseballsavant.mlb.com/csv",
        "file:///etc/passwd",
        "//statsapi.mlb.com/api/v1/schedule",  # protocol-relative
    ],
)
def test_every_host_but_the_allowlisted_two_is_refused(url: str) -> None:
    with pytest.raises(HostNotPermittedError):
        require_permitted_host(url)


def test_both_allowlisted_hosts_are_allowed() -> None:
    """Anti-vacuity: a refusal that refused everything would prove nothing."""
    for host in sorted(MLB_HOSTS):
        require_permitted_host(f"https://{host}/api/v1/schedule")


def test_the_transport_refuses_before_a_socket_exists() -> None:
    transport = UrllibTransport()
    with pytest.raises(HostNotPermittedError):
        transport.get("https://evil.example/api", {"User-Agent": "test"})


def _redirect_to(target: str) -> urllib.request.Request | None:
    handler = PinnedRedirectHandler()
    request = urllib.request.Request(
        "https://statsapi.mlb.com/api/v1/schedule", headers={"User-Agent": "test"}
    )
    return handler.redirect_request(request, None, 302, "Found", email.message.Message(), target)


@pytest.mark.parametrize(
    "target",
    [
        "https://evil.example/api",
        "http://statsapi.mlb.com/api",  # scheme downgrade
        "https://statsapi.mlb.com.evil.example/api",
    ],
)
def test_a_redirect_off_the_allowlist_is_refused(target: str) -> None:
    with pytest.raises(HostNotPermittedError):
        _redirect_to(target)


def test_a_redirect_inside_the_allowlist_is_followed() -> None:
    followed = _redirect_to("https://baseballsavant.mlb.com/leaderboard/statcast?csv=true")
    assert followed is not None
    assert followed.get_full_url().startswith("https://baseballsavant.mlb.com/")


def test_the_transport_installs_the_pinned_redirect_handler() -> None:
    transport = UrllibTransport()
    assert any(isinstance(handler, PinnedRedirectHandler) for handler in transport._opener.handlers)


class _ScriptedTransport:
    """Answers from a script of statuses; records how often it was called."""

    def __init__(self, statuses: list[int]) -> None:
        self._statuses = statuses
        self.calls = 0

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        status = self._statuses[min(self.calls, len(self._statuses) - 1)]
        self.calls += 1
        return HttpResponse(status=status, body=b"{}")


def test_a_transient_status_is_retried_exactly_once() -> None:
    transport = _ScriptedTransport([503, 200])
    response = get_with_retry(
        transport, "https://statsapi.mlb.com/api/v1/schedule", {}, sleep=lambda _: None
    )
    assert response.status == 200
    assert transport.calls == 2


def test_a_persistent_transient_status_is_not_retried_forever() -> None:
    transport = _ScriptedTransport([429])
    response = get_with_retry(
        transport, "https://statsapi.mlb.com/api/v1/schedule", {}, sleep=lambda _: None
    )
    assert response.status == 429
    assert transport.calls == 2


def test_a_non_retryable_status_answers_as_it_arrived() -> None:
    transport = _ScriptedTransport([404])
    response = get_with_retry(
        transport, "https://statsapi.mlb.com/api/v1/schedule", {}, sleep=lambda _: None
    )
    assert response.status == 404
    assert transport.calls == 1
