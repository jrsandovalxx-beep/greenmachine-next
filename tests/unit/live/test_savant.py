"""The Savant CSV adapter against synthetic payloads and scripted transports."""

from __future__ import annotations

from decimal import Decimal

from greenmachine.live.mlb_api import FetchFailure
from greenmachine.live.savant import BaseballSavant
from greenmachine.live.transport import HttpResponse, TransportUnreachableError

# D-124: avg_hit_angle joins the required set (verified live 2026-08 on the
# batter board, the same column the pitcher board carries) — the season
# average launch angle, context only per v2.2 (the ratified read is the
# share of contact above the HR launch floor, not the average).
_STATCAST_CSV = (
    "player_id,attempts,avg_hit_angle,avg_hit_speed,ev95plus,ev95percent,barrels,"
    "brl_percent,anglesweetspotpercent\n"
    "101,300,16.4,91.5,150,50.0,30,10.0,33.3\n"
)

# A batter board missing the launch-angle column fails cleanly — a renamed
# or dropped column must never smuggle in a wrong number.
_STATCAST_CSV_MISSING_COLUMN = (
    "player_id,attempts,avg_hit_speed,ev95plus,ev95percent,barrels,brl_percent,anglesweetspotpercent\n"
    "101,300,91.5,150,50.0,30,10.0,33.3\n"
)

_EXPECTED_CSV = (
    "player_id,pa,bip,ba,slg,woba,est_ba,est_slg,est_woba\n"
    "101,500,380,0.251,0.465,0.340,0.270,0.501,0.362\n"
)

# D-110: a board missing one required column fails cleanly — a renamed or
# dropped column must never smuggle in a wrong number.
_EXPECTED_CSV_MISSING_COLUMN = (
    "player_id,pa,bip,ba,slg,woba,est_ba,est_woba\n101,500,380,0.251,0.465,0.340,0.270,0.362\n"
)

# D-111: the pitcher board publishes the identical metric columns plus
# era/xera and the diff columns (verified live 2026-08) — the parse reads
# the same nine and ignores the rest.
_PITCHER_EXPECTED_CSV = (
    "player_id,pa,bip,ba,est_ba,est_ba_minus_ba_diff,slg,est_slg,est_slg_minus_slg_diff,"
    "woba,est_woba,est_woba_minus_woba_diff,era,xera,era_minus_xera_diff\n"
    "201,620,450,0.240,0.250,0.010,0.410,0.430,0.020,0.294,0.297,0.003,3.46,3.67,-0.206\n"
)

# D-111: the Statcast board against pitchers (verified live 2026-08):
# attempts is the batted balls against; the fbld/gb columns are FB/LD and
# GB exit velocities in mph, not air/ground counts.
_STATCAST_PITCHERS_CSV = (
    "player_id,attempts,avg_hit_angle,anglesweetspotpercent,max_hit_speed,avg_hit_speed,"
    "ev50,fbld,gb,max_distance,avg_distance,avg_hr_distance,ev95plus,ev95percent,barrels,"
    "brl_percent,brl_pa\n"
    "201,100,12.9,32,111.3,88.4,77.8,92.1,86.1,430,157,395,35,35.2,8,8.0,5.2\n"
)

_SPRINT_CSV = (
    "player_id,team_id,team,position,age,competitive_runs,bolts,hp_to_1b,sprint_speed\n"
    "101,147,NYY,CF,26,142,8,4.20,29.4\n"
)

_SQUARED_UP_CSV = (
    "id,name,swings_competitive,percent_swings_competitive,contact,avg_bat_speed,"
    "squared_up_per_bat_contact,squared_up_per_swing\n"
    '101,"Slugger, One",620,0.90,480,73.4,0.41,0.36\n'
)

_TRACKING_CSV = (
    "id,side,avg_bat_speed,attack_angle,ideal_attack_angle_rate,competitive_swings\n"
    "101,R,72.5,12.0,0.55,300\n"
    "101,L,71.0,11.0,0.50,150\n"
)

_BATTED_BALL_CSV = (
    "id,bbe,air_rate,pull_air_rate,straight_air_rate,oppo_air_rate\n101,300,0.42,0.13,0.14,0.15\n"
)

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
    assert row.avg_launch_angle == Decimal("16.4")


def test_statcast_board_fails_cleanly_without_the_launch_angle_column() -> None:
    """D-124: avg_hit_angle is required like every other column on the
    board — a renamed or dropped column fails the whole board, never a
    season LA read over a wrong number."""
    rows = BaseballSavant(_FakeTransport(_STATCAST_CSV_MISSING_COLUMN)).fetch_statcast_batters(
        year=2026
    )
    assert isinstance(rows, FetchFailure)


def test_expected_stats_board_parses_actual_and_expected_rates() -> None:
    """D-110: the revived board carries actual and expected rates side by
    side, so a regression gap's two sides share one denominator."""
    rows = BaseballSavant(_FakeTransport(_EXPECTED_CSV)).fetch_expected_stats(year=2026)
    assert not isinstance(rows, FetchFailure)
    row = rows[101]
    assert row.xwoba == Decimal("0.362")
    assert row.plate_appearances == 500
    assert row.batting_average == Decimal("0.251")
    assert row.slugging == Decimal("0.465")
    assert row.woba == Decimal("0.340")
    assert row.expected_batting_average == Decimal("0.270")
    assert row.expected_slugging == Decimal("0.501")


def test_expected_stats_board_fails_cleanly_on_an_unknown_column() -> None:
    """D-110: a missing est_slg column fails every row's parse, and a board
    with no parseable row is a FetchFailure — never a gap computed over a
    wrong number."""
    result = BaseballSavant(_FakeTransport(_EXPECTED_CSV_MISSING_COLUMN)).fetch_expected_stats(
        year=2026
    )
    assert isinstance(result, FetchFailure)
    assert "no row parsed" in result.reason


def test_pitcher_expected_board_parses_and_ignores_the_era_columns() -> None:
    """D-111: the pitcher board's metric columns are the batter board's —
    the era/xera extras are ignored, never required."""
    rows = BaseballSavant(_FakeTransport(_PITCHER_EXPECTED_CSV)).fetch_pitcher_expected_stats(
        year=2026
    )
    assert not isinstance(rows, FetchFailure)
    row = rows[201]
    assert row.plate_appearances == 620
    assert row.batting_average == Decimal("0.240")
    assert row.slugging == Decimal("0.410")
    assert row.woba == Decimal("0.294")
    assert row.xwoba == Decimal("0.297")
    assert row.expected_batting_average == Decimal("0.250")
    assert row.expected_slugging == Decimal("0.430")


def test_pitcher_expected_board_fails_cleanly_on_an_unknown_column() -> None:
    """D-111: the same unknown-column discipline as the batter board — a
    missing required column is a clean FetchFailure, never a wrong number."""
    savant = BaseballSavant(_FakeTransport(_EXPECTED_CSV_MISSING_COLUMN))
    result = savant.fetch_pitcher_expected_stats(year=2026)
    assert isinstance(result, FetchFailure)
    assert "no row parsed" in result.reason


def test_statcast_pitcher_board_parses_the_against_record() -> None:
    """D-111: batted balls, barrels, and launch angle against — the board
    publishes no air/ground split (fbld/gb are exit velocities). D-128
    (PO): the hard-hit count against reads the board's ev95plus column."""
    rows = BaseballSavant(_FakeTransport(_STATCAST_PITCHERS_CSV)).fetch_statcast_pitchers(year=2026)
    assert not isinstance(rows, FetchFailure)
    row = rows[201]
    assert row.batted_ball_events == 100
    assert row.avg_launch_angle == Decimal("12.9")
    assert row.barrel_count == 8
    assert row.hard_hit_count == 35


def test_a_board_that_loses_half_its_rows_fails_instead_of_shrinking_silently() -> None:
    """D-111 live lesson: when fbld/gb were misread as counts, 809 of 818
    rows dropped silently and every starter read an invented empty board.
    A board that cannot parse half its rows has changed shape — fail it."""
    data_row = _STATCAST_PITCHERS_CSV.split("\n", 1)[1]
    bad_row = data_row.replace("201,", "202,").replace("100,", "not-a-number,", 1)
    worse_row = data_row.replace("201,", "203,").replace("100,", "", 1)
    body = _STATCAST_PITCHERS_CSV + bad_row + worse_row
    rows = BaseballSavant(_FakeTransport(body)).fetch_statcast_pitchers(year=2026)
    assert isinstance(rows, FetchFailure)
    assert "only 1 of 3 rows parsed" in rows.reason


def test_sprint_speed_board_parses() -> None:
    rows = BaseballSavant(_FakeTransport(_SPRINT_CSV)).fetch_sprint_speed(year=2026)
    assert not isinstance(rows, FetchFailure)
    assert rows[101].sprint_speed == Decimal("29.4")


def test_squared_up_board_parses_the_contact_profile() -> None:
    rows = BaseballSavant(_FakeTransport(_SQUARED_UP_CSV)).fetch_squared_up(year=2026)
    assert not isinstance(rows, FetchFailure)
    row = rows[101]
    assert row.competitive_swings == 620
    assert row.squared_up_per_swing == Decimal("0.36")
    assert row.avg_bat_speed == Decimal("73.4")


def test_bat_tracking_keeps_both_sides_of_a_switch_hitter() -> None:
    rows = BaseballSavant(_FakeTransport(_TRACKING_CSV)).fetch_bat_tracking(year=2026)
    assert not isinstance(rows, FetchFailure)
    sides = {row.side: row for row in rows}
    assert sides["R"].competitive_swings == 300
    assert sides["L"].avg_bat_speed == Decimal("71.0")
    assert sides["R"].ideal_attack_angle_share == Decimal("0.55")


def test_batted_ball_board_parses_all_three_air_direction_rates() -> None:
    """The board carries pull, straight and oppo air rates — each a share
    of ALL batted balls, so the three sum to the air share (D-128)."""
    rows = BaseballSavant(_FakeTransport(_BATTED_BALL_CSV)).fetch_batted_ball(year=2026)
    assert not isinstance(rows, FetchFailure)
    assert rows[101].air_share == Decimal("0.42")
    assert rows[101].pull_air_share_of_bbe == Decimal("0.13")
    assert rows[101].straight_air_share_of_bbe == Decimal("0.14")
    assert rows[101].oppo_air_share_of_bbe == Decimal("0.15")
    assert (
        rows[101].pull_air_share_of_bbe
        + rows[101].straight_air_share_of_bbe
        + rows[101].oppo_air_share_of_bbe
        == rows[101].air_share
    )


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
