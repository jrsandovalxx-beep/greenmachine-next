"""The Savant CSV adapter against synthetic payloads and scripted transports."""

from __future__ import annotations

from decimal import Decimal

from greenmachine.live.mlb_api import FetchFailure
from greenmachine.live.savant import BaseballSavant
from greenmachine.live.transport import HttpResponse, TransportUnreachableError

_STATCAST_CSV = (
    "player_id,attempts,avg_hit_speed,ev95plus,ev95percent,barrels,brl_percent,anglesweetspotpercent\n"
    "101,300,91.5,150,50.0,30,10.0,33.3\n"
)

_EXPECTED_CSV = "player_id,pa,bip,est_woba\n101,500,380,0.362\n"

_TRACKING_CSV = (
    "id,side,avg_bat_speed,attack_angle,ideal_attack_angle_rate,competitive_swings\n"
    "101,R,72.5,12.0,0.55,300\n"
    "101,L,71.0,11.0,0.50,150\n"
)

_BATTED_BALL_CSV = "id,bbe,air_rate,pull_air_rate\n101,300,0.42,0.13\n"

_ARSENAL_CSV = (
    "player_id,team_name_alt,pitch_type,pitch_name,pitches,pitch_usage,pa,ba,slg,woba,"
    "whiff_percent,k_percent,put_away,est_woba,hard_hit_percent\n"
    "201,NYY,FF,4-Seam Fastball,900,55.0,220,0.240,0.400,0.300,24.5,22.0,18.0,0.295,38.0\n"
)

_EVENTS_CSV = (
    "game_pk,game_date,batter,pitcher,stand,p_throws,pitch_type,events,description,bb_type,"
    "launch_speed,launch_angle,launch_speed_angle,hc_x,hc_y,estimated_woba_using_speedangle,"
    "woba_value,woba_denom,hit_distance_sc\n"
    "777001,2026-08-20,101,201,L,R,FF,home_run,batted,fly_ball,108.2,28,6,140.5,150.2,1.65,2.0,1,418\n"
    "777001,2026-08-20,101,201,L,R,FF,,foul,,,,,,,,,,\n"
)


class _FakeTransport:
    def __init__(self, csv_text: str, status: int = 200) -> None:
        self._csv_text = csv_text
        self._status = status
        self.requested_urls: list[str] = []

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.requested_urls.append(url)
        return HttpResponse(status=self._status, body=self._csv_text.encode())


def test_statcast_board_normalizes_percents_to_fractions() -> None:
    rows = BaseballSavant(_FakeTransport(_STATCAST_CSV)).fetch_statcast_batters(year=2026)
    assert not isinstance(rows, FetchFailure)
    row = rows[101]
    assert row.batted_ball_events == 300
    assert row.exit_velocity_avg == Decimal("91.5")
    assert row.hard_hit_share == Decimal("0.5")  # derived from count over attempts
    assert row.barrel_share == Decimal("0.1")
    assert row.sweet_spot_share == Decimal("0.333")


def test_expected_stats_board_parses() -> None:
    rows = BaseballSavant(_FakeTransport(_EXPECTED_CSV)).fetch_expected_stats(year=2026)
    assert not isinstance(rows, FetchFailure)
    assert rows[101].xwoba == Decimal("0.362")
    assert rows[101].plate_appearances == 500


def test_bat_tracking_keeps_both_sides_of_a_switch_hitter() -> None:
    rows = BaseballSavant(_FakeTransport(_TRACKING_CSV)).fetch_bat_tracking(year=2026)
    assert not isinstance(rows, FetchFailure)
    sides = {row.side: row for row in rows}
    assert sides["R"].competitive_swings == 300
    assert sides["L"].avg_bat_speed == Decimal("71.0")
    assert sides["R"].ideal_attack_angle_share == Decimal("0.55")


def test_batted_ball_board_parses_air_and_pull_rates() -> None:
    rows = BaseballSavant(_FakeTransport(_BATTED_BALL_CSV)).fetch_batted_ball(year=2026)
    assert not isinstance(rows, FetchFailure)
    assert rows[101].air_share == Decimal("0.42")
    assert rows[101].pull_air_share_of_bbe == Decimal("0.13")


def test_pitch_arsenal_parses_per_pitch_rows() -> None:
    rows = BaseballSavant(_FakeTransport(_ARSENAL_CSV)).fetch_pitch_arsenal(
        kind="pitcher", year=2026
    )
    assert not isinstance(rows, FetchFailure)
    row = rows[0]
    assert row.player_id == 201
    assert row.team == "NYY"
    assert row.usage_share == Decimal("0.55")
    assert row.whiff_share == Decimal("0.245")
    assert row.put_away_share == Decimal("0.18")


def test_pitch_events_classify_contact_and_leave_fouls_unclassified() -> None:
    events = BaseballSavant(_FakeTransport(_EVENTS_CSV)).fetch_pitch_events(
        year=2026, day="2026-08-20"
    )
    assert not isinstance(events, FetchFailure)
    homer, foul = events
    assert homer.launch_speed_angle == 6
    assert homer.launch_speed == Decimal("108.2")
    assert homer.hit_distance == Decimal("418")
    assert foul.hit_distance is None
    assert homer.batter_side == "L"
    assert foul.launch_speed_angle is None
    assert foul.launch_speed is None
    assert foul.event == ""


def test_a_non_200_status_becomes_a_fetch_failure() -> None:
    failure = BaseballSavant(_FakeTransport("", status=503)).fetch_statcast_batters(year=2026)
    assert isinstance(failure, FetchFailure)
    assert "HTTP 503" in failure.reason


def test_a_malformed_csv_becomes_a_fetch_failure() -> None:
    failure = BaseballSavant(_FakeTransport("a,b\n1\n")).fetch_statcast_batters(year=2026)
    assert isinstance(failure, FetchFailure)


def test_a_transport_error_becomes_a_fetch_failure() -> None:
    class _Down:
        def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
            raise TransportUnreachableError("no route")

    failure = BaseballSavant(_Down()).fetch_batted_ball(year=2026)
    assert isinstance(failure, FetchFailure)
    assert "transport failed" in failure.reason


def test_every_board_request_stays_on_the_savant_host() -> None:
    transport = _FakeTransport(_STATCAST_CSV)
    BaseballSavant(transport).fetch_statcast_batters(year=2026)
    assert all(
        url.startswith("https://baseballsavant.mlb.com/") for url in transport.requested_urls
    )


def test_a_byte_order_mark_does_not_shift_the_columns() -> None:
    """Regression: Savant prepends a BOM; unhandled, it shifts every column."""
    bom_csv = "\ufeff" + _STATCAST_CSV
    rows = BaseballSavant(_FakeTransport(bom_csv)).fetch_statcast_batters(year=2026)
    assert not isinstance(rows, FetchFailure)
    assert rows[101].batted_ball_events == 300
