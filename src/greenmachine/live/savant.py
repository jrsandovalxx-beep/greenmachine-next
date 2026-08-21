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
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

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
    player_id: int
    batted_ball_events: int
    exit_velocity_avg: Decimal
    hard_hit_count: int
    hard_hit_share: Decimal
    barrel_count: int
    barrel_share: Decimal
    sweet_spot_share: Decimal


@dataclass(frozen=True)
class ExpectedStatsRow:
    player_id: int
    plate_appearances: int
    balls_in_play: int
    xwoba: Decimal


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
    player_id: int
    batted_ball_events: int
    air_share: Decimal  # fraction of BBE that are air balls
    pull_air_share_of_bbe: Decimal  # fraction of ALL BBE that are pulled air balls


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


def _parse_rows(rows: list[dict[str, str]], context: str, parse: Any) -> list[Any]:
    """Parse each row; drop the unparseable tiny-sample rows Savant ships.

    A row with an empty required numeric is almost always a near-zero-sample
    row. Dropping it is honest — it was never a measurement — while failing
    the whole board over it would manufacture a source outage. If nothing
    parses at all, the payload is malformed and the board fails.
    """
    parsed: list[Any] = []
    for row in rows:
        try:
            parsed.append(parse(row))
        except PayloadMalformedError:
            continue
    if rows and not parsed:
        raise PayloadMalformedError(f"{context}: no row parsed")
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

    def fetch_statcast_batters(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, StatcastBatterRow] | FetchFailure:
        """Season Statcast quality-of-contact board, keyed by player id."""
        context = "statcast-batters"
        rows = self._get_csv(_STATCAST_BATTERS_URL.format(year=year, minimum=minimum), context)
        if isinstance(rows, FetchFailure):
            return rows

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
            )

        try:
            parsed = _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return {row.player_id: row for row in parsed}

    def fetch_expected_stats(self, *, year: int) -> dict[int, ExpectedStatsRow] | FetchFailure:
        """Season expected-statistics board (xwOBA), keyed by player id."""
        context = "expected-stats"
        rows = self._get_csv(_EXPECTED_STATS_URL.format(year=year), context)
        if isinstance(rows, FetchFailure):
            return rows

        def parse(row: dict[str, str]) -> ExpectedStatsRow:
            player_id = _int(row.get("player_id"), context)
            return ExpectedStatsRow(
                player_id=player_id,
                plate_appearances=_int(row.get("pa"), context),
                balls_in_play=_int(row.get("bip"), context),
                xwoba=_decimal(row.get("est_woba"), context),
            )

        try:
            parsed = _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return {row.player_id: row for row in parsed}

    def fetch_bat_tracking(
        self, *, year: int, minimum: int = 0, start: str = "", end: str = ""
    ) -> tuple[BatTrackingRow, ...] | FetchFailure:
        """Bat-tracking rows (one per player per batting side).

        ``start``/``end`` are ISO dates; empty strings mean season-to-date.
        """
        context = "bat-tracking"
        rows = self._get_csv(
            _BAT_TRACKING_URL.format(year=year, minimum=minimum, start=start, end=end),
            context,
        )
        if isinstance(rows, FetchFailure):
            return rows

        def parse(row: dict[str, str]) -> BatTrackingRow:
            return BatTrackingRow(
                player_id=_int(row.get("id"), context),
                side=str(row.get("side", "")).strip(),
                avg_bat_speed=_decimal(row.get("avg_bat_speed"), context),
                attack_angle=_decimal(row.get("attack_angle"), context),
                ideal_attack_angle_share=_decimal(row.get("ideal_attack_angle_rate"), context),
                competitive_swings=_int(row.get("competitive_swings"), context),
            )

        try:
            parsed = _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return tuple(parsed)

    def fetch_batted_ball(
        self, *, year: int, minimum: int = 0
    ) -> dict[int, BattedBallRow] | FetchFailure:
        """Season batted-ball profile board (air rate, pull-air rate)."""
        context = "batted-ball"
        rows = self._get_csv(_BATTED_BALL_URL.format(year=year, minimum=minimum), context)
        if isinstance(rows, FetchFailure):
            return rows

        def parse(row: dict[str, str]) -> BattedBallRow:
            player_id = _int(row.get("id"), context)
            return BattedBallRow(
                player_id=player_id,
                batted_ball_events=_int(row.get("bbe"), context),
                air_share=_decimal(row.get("air_rate"), context),
                pull_air_share_of_bbe=_decimal(row.get("pull_air_rate"), context),
            )

        try:
            parsed = _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return {row.player_id: row for row in parsed}

    def fetch_pitch_arsenal(
        self, *, kind: Literal["pitcher", "batter"], year: int
    ) -> tuple[PitchArsenalRow, ...] | FetchFailure:
        """Per-pitch-type arsenal rows for pitchers or batters."""
        context = f"pitch-arsenal-{kind}"
        rows = self._get_csv(_PITCH_ARSENAL_URL.format(kind=kind, year=year), context)
        if isinstance(rows, FetchFailure):
            return rows

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

        try:
            parsed = _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return tuple(parsed)

    def fetch_pitch_events(self, *, year: int, day: str) -> tuple[PitchEvent, ...] | FetchFailure:
        """Every pitch of one calendar day (``day`` is ISO ``YYYY-MM-DD``)."""
        context = f"pitch-events[{day}]"
        rows = self._get_csv(_PITCH_EVENTS_URL.format(year=year, day=day), context)
        if isinstance(rows, FetchFailure):
            return rows

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

        try:
            parsed = _parse_rows(rows, context, parse)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return tuple(parsed)
