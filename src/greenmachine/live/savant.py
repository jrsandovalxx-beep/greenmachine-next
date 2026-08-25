"""The Baseball Savant adapter (D-070): Statcast boards and per-pitch events.

Savant serves leaderboards as CSV downloads behind ``csv=true`` and expects a
browser User-Agent. All six endpoint shapes are module constants; every parse
is defensive, and failures surface as :class:`~greenmachine.live.mlb_api.FetchFailure`
so the assembly layer can degrade to named absences.

Percent columns arrive as percent-points (``42.5``) and are normalized to
fractions (``0.425``) at the boundary, once, by :func:`_percent`; every rate
that leaves this module is a :class:`Decimal` fraction unless the field name
says otherwise.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypeVar

from greenmachine.live.mlb_api import FetchFailure
from greenmachine.live.transport import (
    Transport,
    TransportError,
    get_with_retry,
)

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/csv,*/*"}

_STATCAST_BATTERS_URL = (
    "https://baseballsavant.mlb.com/leaderboard/statcast"
    "?type=batter&year={year}&min={minimum}&csv=true"
)
_EXPECTED_STATS_URL = (
    "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
    "?type=batter&year={year}&min=0&csv=true"
)
# D-111: the same expected-statistics board against pitchers — identical
# metric columns plus era/xera, which this read ignores (verified live
# 2026-08). The header cards and the Arms tab read wOBA/xwOBA and ISO/xISO
# against from it.
_EXPECTED_PITCHER_STATS_URL = (
    "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
    "?type=pitcher&year={year}&min=0&csv=true"
)
# D-111: the season Statcast board against pitchers. Verified live 2026-08:
# columns player_id, attempts, avg_hit_angle, barrels (among others) —
# attempts the batted balls against, avg_hit_angle the average launch angle
# against. The fbld/gb columns on this board are FB/LD and GB exit
# velocities in mph, NOT air/ground counts — this board publishes no
# air-ball split against, so the season air share stays a named absence
# (the L30 events carry the real bb_type split).
_STATCAST_PITCHERS_URL = (
    "https://baseballsavant.mlb.com/leaderboard/statcast"
    "?type=pitcher&year={year}&min={minimum}&csv=true"
)
_SPRINT_SPEED_URL = (
    "https://baseballsavant.mlb.com/leaderboard/sprint_speed?year={year}&min=0&csv=true"
)
# D-110: the bat-tracking family's contact board — one row per batter (no
# side split), carrying squared-up-per-swing and bat speed over competitive
# swings. Verified live 2026-08: columns id, swings_competitive,
# squared_up_per_swing, avg_bat_speed.
_SQUARED_UP_URL = (
    "https://baseballsavant.mlb.com/leaderboard/bat-tracking"
    "?csv=true&batSide=&dateStart=&dateEnd=&minSwings={minimum}&year={year}"
)
_BAT_TRACKING_URL = (
    "https://baseballsavant.mlb.com/leaderboard/bat-tracking/swing-path-attack-angle"
    "?csv=true&batSide=&dateStart={start}&dateEnd={end}&minSwings={minimum}&year={year}"
)
_BATTED_BALL_URL = (
    "https://baseballsavant.mlb.com/leaderboard/batted-ball"
    "?type=batter&year={year}&min={minimum}&csv=true"
)
_PITCH_ARSENAL_URL = (
    "https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats"
    "?type={kind}&year={year}&min=0&csv=true"
)
_PITCH_EVENTS_URL = (
    "https://baseballsavant.mlb.com/statcast_search/csv"
    "?all=true&hfSea={year}%7C&player_type=batter"
    "&game_date_gt={day}&game_date_lt={day}&type=details&"
)


class PayloadMalformedError(Exception):
    """The response was 200 but not the CSV shape this adapter parses."""


@dataclass(frozen=True)
class StatcastBatterRow:
    """Season Statcast quality-of-contact board, one batter per row. Every
    column is required — a renamed or dropped column fails the whole board
    cleanly, never a wrong number. ``avg_launch_angle`` is the board's
    ``avg_hit_angle`` (verified live 2026-08 on the batter type, the same
    column the pitcher board carries) — a season average, so it is context
    only: v2.2 reads the share of contact above the HR launch floor, not
    the average."""

    player_id: int
    batted_ball_events: int
    exit_velocity_avg: Decimal
    hard_hit_count: int
    hard_hit_share: Decimal
    barrel_count: int
    barrel_share: Decimal
    sweet_spot_share: Decimal
    avg_launch_angle: Decimal


@dataclass(frozen=True)
class ExpectedStatsRow:
    """The season expected-statistics board (D-110): actual and expected
    rates side by side off the one board, so a regression gap's two sides
    share a denominator. Every column is required — an unknown column is a
    clean FetchFailure, never a wrong number."""

    player_id: int
    plate_appearances: int
    balls_in_play: int
    batting_average: Decimal
    slugging: Decimal
    woba: Decimal
    expected_batting_average: Decimal
    expected_slugging: Decimal
    xwoba: Decimal


@dataclass(frozen=True)
class StatcastPitcherRow:
    """The season Statcast board against one pitcher (D-111): batted balls,
    barrels, average launch angle, and — D-128 (PO) — the hard-hit count
    against (the board's ev95plus column, verified live 2026-08-25). Every
    column is required — an unknown column is a clean FetchFailure, never a
    wrong number. The board's fbld/gb columns are exit velocities, not
    counts, so no air/ground split is read here."""

    player_id: int
    batted_ball_events: int
    avg_launch_angle: Decimal
    barrel_count: int
    hard_hit_count: int


@dataclass(frozen=True)
class SprintSpeedRow:
    """One batter's season sprint speed in feet per second (D-110)."""

    player_id: int
    sprint_speed: Decimal


@dataclass(frozen=True)
class SquaredUpRow:
    """One batter's season contact-quality line (D-110): squared-up share of
    competitive swings and mean bat speed, both sides of the contact-first
    profile. The board publishes one row per batter — no side split."""

    player_id: int
    competitive_swings: int
    squared_up_per_swing: Decimal
    avg_bat_speed: Decimal


@dataclass(frozen=True)
class BatTrackingRow:
    player_id: int
    side: str  # "R" or "L" — a switch hitter has one row per side
    avg_bat_speed: Decimal
    attack_angle: Decimal
    ideal_attack_angle_share: Decimal
    competitive_swings: int


@dataclass(frozen=True)
class BattedBallRow:
    """The season batted-ball profile board for one batter: batted balls,
    the air share, and the three air-direction rates — each a share of ALL
    batted balls, so the three sum to the air share (verified live
    2026-08-25). D-128 (PO): the season view's pull/straight/oppo air
    reads come from this board — published numbers, never home-built
    derivations; the per-air-ball shares the grid prints are computed
    pipeline-side off these rates (§GMF-008)."""

    player_id: int
    batted_ball_events: int
    air_share: Decimal  # fraction of BBE that are air balls
    pull_air_share_of_bbe: Decimal  # fraction of ALL BBE that are pulled air balls
    straight_air_share_of_bbe: Decimal
    oppo_air_share_of_bbe: Decimal


@dataclass(frozen=True)
class PitchArsenalRow:
    player_id: int
    team: str  # Savant's alt code ("NYY", "ATH", ...) — "" when absent
    pitch_type: str
    pitch_name: str
    pitches: int
    usage_share: Decimal
    plate_appearances: int
    batting_average: Decimal
    slugging: Decimal
    woba: Decimal
    whiff_share: Decimal
    strikeout_share: Decimal
    put_away_share: Decimal
    expected_woba: Decimal
    hard_hit_share: Decimal | None  # the column has shipped empty; read, never required


@dataclass(frozen=True)
class PitchEvent:
    """One pitch from the per-event search CSV, trimmed to what form needs."""

    game_pk: int
    game_date: str
    batter_id: int
    pitcher_id: int
    batter_side: str
    pitcher_throws: str
    pitch_type: str
    event: str
    description: str
    bb_type: str
    launch_speed: Decimal | None
    launch_angle: Decimal | None
    launch_speed_angle: int | None  # 1..6 classification; 6 is the barrel band
    hc_x: Decimal | None
    hc_y: Decimal | None
    estimated_woba: Decimal | None
    woba_value: Decimal | None
    woba_denom: Decimal | None
    hit_distance: Decimal | None = None


def _decimal(raw: Any, context: str) -> Decimal:
    if raw is None:
        raise PayloadMalformedError(f"{context}: missing numeric value")
    text = str(raw).strip()
    if not text:
        raise PayloadMalformedError(f"{context}: missing numeric value")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise PayloadMalformedError(f"{context}: not numeric ({text!r})") from exc


def _decimal_or_none(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _int(raw: Any, context: str) -> int:
    text = str(raw).strip() if raw is not None else ""
    if not text:
        raise PayloadMalformedError(f"{context}: missing integer value")
    try:
        return int(text)
    except ValueError as exc:
        raise PayloadMalformedError(f"{context}: not an integer ({text!r})") from exc


def _int_or_none(raw: Any) -> int | None:
    text = str(raw).strip() if raw is not None else ""
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _percent(raw: Any, context: str) -> Decimal:
    """Savant percent column (percent-points) to a fraction."""
    return _decimal(raw, context) / Decimal(100)


def _percent_or_none(raw: Any) -> Decimal | None:
    value = _decimal_or_none(raw)
    return value / Decimal(100) if value is not None else None


def _parse_expected_row(row: dict[str, str], context: str) -> ExpectedStatsRow:
    """One expected-statistics row, batter or pitcher board (D-111): the two
    boards publish the identical metric columns, and every parsed column is
    required — an unknown column is a clean FetchFailure, never a wrong
    number."""
    return ExpectedStatsRow(
        player_id=_int(row.get("player_id"), context),
        plate_appearances=_int(row.get("pa"), context),
        balls_in_play=_int(row.get("bip"), context),
        batting_average=_decimal(row.get("ba"), context),
        slugging=_decimal(row.get("slg"), context),
        woba=_decimal(row.get("woba"), context),
        expected_batting_average=_decimal(row.get("est_ba"), context),
        expected_slugging=_decimal(row.get("est_slg"), context),
        xwoba=_decimal(row.get("est_woba"), context),
    )


_T = TypeVar("_T")


def _parse_rows(
    rows: list[dict[str, str]], context: str, parse: Callable[[dict[str, str]], _T]
) -> list[_T]:
    """Parse each row; drop the unparseable tiny-sample rows Savant ships.

    A row with an empty required numeric is almost always a near-zero-sample
    row. Dropping it is honest — it was never a measurement — while failing
    the whole board over it would manufacture a source outage. If nothing
    parses at all, the payload is malformed and the board fails.
    """
    parsed: list[_T] = []
    for row in rows:
        try:
            parsed.append(parse(row))
        except PayloadMalformedError:
            continue
    if rows and not parsed:
        raise PayloadMalformedError(f"{context}: no row parsed")
    if len(parsed) < len(rows) / 2:
        # Losing isolated tiny-sample rows is honest; losing half the board
        # means the payload changed shape and every miss after this would be
        # a silent absence — fail the board instead (D-111's live lesson).
        raise PayloadMalformedError(f"{context}: only {len(parsed)} of {len(rows)} rows parsed")
    return parsed


def _rows(body: bytes, context: str) -> list[dict[str, str]]:
    # utf-8-sig, deliberately: Savant prepends a BOM, and left in place it
    # glues itself to the first (quoted) header cell, which then mis-splits
    # "last_name, first_name" and shifts every column one place left.
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PayloadMalformedError(f"{context}: body is not UTF-8") from exc
    if not text.strip():
        return []  # a 200 with an empty body: no data for that day
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise PayloadMalformedError(f"{context}: empty CSV")
    return [dict(row) for row in reader]


class BaseballSavant:
    """Reads Savant CSV boards through an injected, host-pinned transport."""

    __slots__ = ("_transport",)

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def _get_csv(self, url: str, context: str) -> list[dict[str, str]] | FetchFailure:
        try:
            response = get_with_retry(self._transport, url, _HEADERS)
        except TransportError as exc:
            return FetchFailure(f"{context}: transport failed ({exc})")
        if response.status != 200:
            return FetchFailure(f"{context}: HTTP {response.status}")
        try:
            return _rows(response.body, context)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))

    def _board(
        self, url: str, context: str, parse: Callable[[dict[str, str]], _T]
    ) -> list[_T] | FetchFailure:
        """One board read: the CSV fetched and parsed row-wise, every failure
        surfaced as a :class:`FetchFailure` — the shape all six boards share."""
        rows = self._get_csv(url, context)
        if isinstance(rows, FetchFailure):
            return rows
        try:
            return _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))

    def fetch_statcast_batters(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, StatcastBatterRow] | FetchFailure:
        """Season Statcast quality-of-contact board, keyed by player id."""
        context = "statcast-batters"

        def parse(row: dict[str, str]) -> StatcastBatterRow:
            player_id = _int(row.get("player_id"), context)
            attempts = _int(row.get("attempts"), context)
            ev95 = _int(row.get("ev95plus"), context)
            barrels = _int(row.get("barrels"), context)
            return StatcastBatterRow(
                player_id=player_id,
                batted_ball_events=attempts,
                exit_velocity_avg=_decimal(row.get("avg_hit_speed"), context),
                hard_hit_count=ev95,
                hard_hit_share=(Decimal(ev95) / Decimal(attempts) if attempts else Decimal(0)),
                barrel_count=barrels,
                barrel_share=_percent(row.get("brl_percent"), context),
                sweet_spot_share=_percent(row.get("anglesweetspotpercent"), context),
                avg_launch_angle=_decimal(row.get("avg_hit_angle"), context),
            )

        parsed = self._board(
            _STATCAST_BATTERS_URL.format(year=year, minimum=minimum), context, parse
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_expected_stats(self, *, year: int) -> dict[int, ExpectedStatsRow] | FetchFailure:
        """Season expected-statistics board, keyed by player id (D-110).

        The board carries actual and expected rates side by side (verified
        live 2026-08: ba/slg/woba beside est_ba/est_slg/est_woba); every one
        is required, so a renamed or dropped column fails the whole board
        cleanly rather than smuggling in a wrong number.
        """
        context = "expected-stats"
        parsed = self._board(
            _EXPECTED_STATS_URL.format(year=year),
            context,
            lambda row: _parse_expected_row(row, context),
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_pitcher_expected_stats(
        self, *, year: int
    ) -> dict[int, ExpectedStatsRow] | FetchFailure:
        """Season expected-statistics board against pitchers (D-111), keyed
        by player id. Same metric columns as the batter board (the pitcher's
        adds era/xera, ignored here); every parsed column is required, so a
        renamed or dropped column fails the whole board cleanly."""
        context = "pitcher-expected-stats"
        parsed = self._board(
            _EXPECTED_PITCHER_STATS_URL.format(year=year),
            context,
            lambda row: _parse_expected_row(row, context),
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_statcast_pitchers(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, StatcastPitcherRow] | FetchFailure:
        """Season Statcast quality-of-contact board against pitchers (D-111),
        keyed by player id. Batted balls, barrels, average launch angle, and
        the hard-hit count against (D-128); every column required."""
        context = "statcast-pitchers"

        def parse(row: dict[str, str]) -> StatcastPitcherRow:
            return StatcastPitcherRow(
                player_id=_int(row.get("player_id"), context),
                batted_ball_events=_int(row.get("attempts"), context),
                avg_launch_angle=_decimal(row.get("avg_hit_angle"), context),
                barrel_count=_int(row.get("barrels"), context),
                hard_hit_count=_int(row.get("ev95plus"), context),
            )

        parsed = self._board(
            _STATCAST_PITCHERS_URL.format(year=year, minimum=minimum), context, parse
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_sprint_speed(self, *, year: int) -> dict[int, SprintSpeedRow] | FetchFailure:
        """Season sprint-speed leaderboard (feet per second), keyed by player
        id (D-110)."""
        context = "sprint-speed"

        def parse(row: dict[str, str]) -> SprintSpeedRow:
            return SprintSpeedRow(
                player_id=_int(row.get("player_id"), context),
                sprint_speed=_decimal(row.get("sprint_speed"), context),
            )

        parsed = self._board(_SPRINT_SPEED_URL.format(year=year), context, parse)
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_squared_up(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, SquaredUpRow] | FetchFailure:
        """Season contact-quality board: squared-up share of competitive
        swings and mean bat speed, keyed by player id (D-110). One row per
        batter — the board publishes no side split."""
        context = "squared-up"

        def parse(row: dict[str, str]) -> SquaredUpRow:
            return SquaredUpRow(
                player_id=_int(row.get("id"), context),
                competitive_swings=_int(row.get("swings_competitive"), context),
                squared_up_per_swing=_decimal(row.get("squared_up_per_swing"), context),
                avg_bat_speed=_decimal(row.get("avg_bat_speed"), context),
            )

        parsed = self._board(_SQUARED_UP_URL.format(year=year, minimum=minimum), context, parse)
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_bat_tracking(
        self, *, year: int, minimum: int = 0, start: str = "", end: str = ""
    ) -> tuple[BatTrackingRow, ...] | FetchFailure:
        """Bat-tracking rows (one per player per batting side).

        ``start``/``end`` are ISO dates; empty strings mean season-to-date.
        """
        context = "bat-tracking"

        def parse(row: dict[str, str]) -> BatTrackingRow:
            return BatTrackingRow(
                player_id=_int(row.get("id"), context),
                side=str(row.get("side", "")).strip(),
                avg_bat_speed=_decimal(row.get("avg_bat_speed"), context),
                attack_angle=_decimal(row.get("attack_angle"), context),
                ideal_attack_angle_share=_decimal(row.get("ideal_attack_angle_rate"), context),
                competitive_swings=_int(row.get("competitive_swings"), context),
            )

        parsed = self._board(
            _BAT_TRACKING_URL.format(year=year, minimum=minimum, start=start, end=end),
            context,
            parse,
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        return tuple(parsed)

    def fetch_batted_ball(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, BattedBallRow] | FetchFailure:
        """Season batted-ball profile board: air rate plus the three
        air-direction rates (pull/straight/oppo), each over all batted
        balls (D-128)."""
        context = "batted-ball"

        def parse(row: dict[str, str]) -> BattedBallRow:
            player_id = _int(row.get("id"), context)
            return BattedBallRow(
                player_id=player_id,
                batted_ball_events=_int(row.get("bbe"), context),
                air_share=_decimal(row.get("air_rate"), context),
                pull_air_share_of_bbe=_decimal(row.get("pull_air_rate"), context),
                straight_air_share_of_bbe=_decimal(row.get("straight_air_rate"), context),
                oppo_air_share_of_bbe=_decimal(row.get("oppo_air_rate"), context),
            )

        parsed = self._board(_BATTED_BALL_URL.format(year=year, minimum=minimum), context, parse)
        if isinstance(parsed, FetchFailure):
            return parsed
        return {row.player_id: row for row in parsed}

    def fetch_pitch_arsenal(
        self, *, kind: Literal["pitcher", "batter"], year: int
    ) -> tuple[PitchArsenalRow, ...] | FetchFailure:
        """Per-pitch-type arsenal rows for pitchers or batters."""
        context = f"pitch-arsenal-{kind}"

        def parse(row: dict[str, str]) -> PitchArsenalRow:
            return PitchArsenalRow(
                player_id=_int(row.get("player_id"), context),
                team=str(row.get("team_name_alt", "") or "").strip(),
                pitch_type=str(row.get("pitch_type", "")).strip(),
                pitch_name=str(row.get("pitch_name", "") or "").strip(),
                pitches=_int(row.get("pitches"), context),
                usage_share=_percent(row.get("pitch_usage"), context),
                plate_appearances=_int(row.get("pa"), context),
                batting_average=_decimal(row.get("ba"), context),
                slugging=_decimal(row.get("slg"), context),
                woba=_decimal(row.get("woba"), context),
                whiff_share=_percent(row.get("whiff_percent"), context),
                strikeout_share=_percent(row.get("k_percent"), context),
                put_away_share=_percent(row.get("put_away"), context),
                expected_woba=_decimal(row.get("est_woba"), context),
                hard_hit_share=_percent_or_none(row.get("hard_hit_percent")),
            )

        parsed = self._board(_PITCH_ARSENAL_URL.format(kind=kind, year=year), context, parse)
        if isinstance(parsed, FetchFailure):
            return parsed
        return tuple(parsed)

    def fetch_pitch_events(self, *, year: int, day: str) -> tuple[PitchEvent, ...] | FetchFailure:
        """Every pitch of one calendar day (``day`` is ISO ``YYYY-MM-DD``)."""
        context = f"pitch-events[{day}]"

        def parse(row: dict[str, str]) -> PitchEvent:
            return PitchEvent(
                game_pk=_int(row.get("game_pk"), context),
                game_date=str(row.get("game_date", "")).strip(),
                batter_id=_int(row.get("batter"), context),
                pitcher_id=_int(row.get("pitcher"), context),
                batter_side=str(row.get("stand", "")).strip(),
                pitcher_throws=str(row.get("p_throws", "")).strip(),
                pitch_type=str(row.get("pitch_type", "")).strip(),
                event=str(row.get("events", "") or "").strip(),
                description=str(row.get("description", "") or "").strip(),
                bb_type=str(row.get("bb_type", "") or "").strip(),
                launch_speed=_decimal_or_none(row.get("launch_speed")),
                launch_angle=_decimal_or_none(row.get("launch_angle")),
                launch_speed_angle=_int_or_none(row.get("launch_speed_angle")),
                hc_x=_decimal_or_none(row.get("hc_x")),
                hc_y=_decimal_or_none(row.get("hc_y")),
                estimated_woba=_decimal_or_none(row.get("estimated_woba_using_speedangle")),
                woba_value=_decimal_or_none(row.get("woba_value")),
                woba_denom=_decimal_or_none(row.get("woba_denom")),
                hit_distance=_decimal_or_none(row.get("hit_distance_sc")),
            )

        parsed = self._board(_PITCH_EVENTS_URL.format(year=year, day=day), context, parse)
        if isinstance(parsed, FetchFailure):
            return parsed
        return tuple(parsed)
