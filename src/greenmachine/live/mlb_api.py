"""The MLB Stats API adapter (D-070): slate, lineups, and season counts.

Everything this module knows about the outside world is three endpoint
templates — module constants, never caller-supplied — and the JSON shapes
they answer with. All parsing is defensive: any malformed payload becomes
:class:`PayloadMalformedError`, every transport failure is caught, and both
surface to the caller as :class:`FetchFailure`, which the assembly layer maps
to the contract's named absence states (§GMF-006 criterion 3(c)).

No clock is read here: the slate date is a parameter. No cache lives here:
caching is the composition root's business (D-070), so a reload is not a
refetch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from greenmachine.live.transport import (
    Transport,
    TransportError,
    get_with_retry,
)

_SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&hydrate=probablePitcher"
)
_BOXSCORE_URL = "https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
_GAME_LOGS_URL = (
    "https://statsapi.mlb.com/api/v1/people"
    "?personIds={ids}&hydrate=stats(group=%5Bhitting%5D,type=%5BgameLog%5D,"
    "startDate={start},endDate={end})"
)
_SEASON_STATS_URL = (
    "https://statsapi.mlb.com/api/v1/people"
    "?personIds={ids}&hydrate=stats(group=%5B{group}%5D,type=%5Bseason%5D)"
)

# The Stats API answers without one, but an identifying agent is honest.
USER_AGENT = "GreenMachineNext/1.0 (mlb research dashboard)"
_HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


class PayloadMalformedError(Exception):
    """The response was 200 but not the JSON shape this adapter parses."""


@dataclass(frozen=True)
class FetchFailure:
    """A fetch that produced nothing usable, with a plain-language reason.

    The assembly layer turns this into the contract's ``SOURCE_UNAVAILABLE``
    absence; the reason text is diagnostics, never a rendered value.
    """

    reason: str


@dataclass(frozen=True)
class ProbablePitcher:
    player_id: int
    full_name: str


@dataclass(frozen=True)
class ScheduledGame:
    game_pk: int
    official_date: str  # ISO calendar date the API schedules the game on
    game_datetime_utc: str  # ISO instant ("2026-08-20T16:35:00Z"), "" when absent
    status: str  # e.g. "Final", "Scheduled", "In Progress"
    venue_id: int
    venue_name: str
    home_team: str
    away_team: str
    home_probable: ProbablePitcher | None
    away_probable: ProbablePitcher | None


@dataclass(frozen=True)
class Slate:
    official_date: str
    games: tuple[ScheduledGame, ...]


@dataclass(frozen=True)
class BattingOrders:
    """Posted batting orders for one game; empty tuples mean not posted yet."""

    game_pk: int
    home: tuple[int, ...]
    away: tuple[int, ...]


@dataclass(frozen=True)
class SeasonHittingLine:
    """Season hitting counts (D-064's AB/H/K live here, raw and observed)."""

    player_id: int
    full_name: str
    bats: str  # "R", "L", or "S" (switch); "" when the API does not say
    games: int
    plate_appearances: int
    at_bats: int
    hits: int
    home_runs: int
    strikeouts: int
    total_bases: int = 0
    # D-110: sacrifice flies, the BABIP denominator's missing term —
    # (H-HR)/(AB-K-HR+SF). Defaulted so pre-SP-2 fixtures stay valid.
    sacrifice_flies: int = 0


@dataclass(frozen=True)
class GameLogEntry:
    """One completed-game line from a batter's hitting game log (D-100).

    The game log lists only games already final, in date order — the
    near-real-time record Savant's day-indexed search CSV cannot be.
    """

    date: str  # ISO YYYY-MM-DD
    game_pk: int
    home_runs: int
    plate_appearances: int


@dataclass(frozen=True)
class SeasonPitchingLine:
    player_id: int
    full_name: str
    throws: str  # "R" or "L"; "" when the API does not say
    games_started: int
    innings_pitched: str  # MLB's baseball notation: .1/.2 are outs, kept as text
    era: str
    whip: str
    strikeouts: int
    batters_faced: int
    # D-111: home runs allowed, the HR/9 numerator on the starter header
    # cards and the Arms tab. Defaulted so pre-D-111 fixtures stay valid.
    home_runs: int = 0


def _parse_json(body: bytes, context: str) -> Any:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadMalformedError(f"{context}: body is not UTF-8") from exc
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadMalformedError(f"{context}: body is not JSON") from exc
    return parsed


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PayloadMalformedError(f"{context}: expected an object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise PayloadMalformedError(f"{context}: expected an array")
    return value


def _require_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PayloadMalformedError(f"{context}: expected an integer, got {value!r}")
    return value


def _require_str(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise PayloadMalformedError(f"{context}: expected a non-empty string")
    return value


def _optional_int(mapping: dict[str, Any], key: str, context: str) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    return _require_int(value, f"{context}.{key}")


def _probable(team_block: dict[str, Any], context: str) -> ProbablePitcher | None:
    raw = team_block.get("probablePitcher")
    if raw is None:
        return None
    pitcher = _require_mapping(raw, f"{context}.probablePitcher")
    player_id = _require_int(pitcher.get("id"), f"{context}.probablePitcher.id")
    name = pitcher.get("fullName")
    return ProbablePitcher(
        player_id=player_id,
        full_name=name if isinstance(name, str) and name else "",
    )


def _parse_game(raw: Any, context: str) -> ScheduledGame:
    game = _require_mapping(raw, context)
    teams = _require_mapping(game.get("teams"), f"{context}.teams")
    home = _require_mapping(teams.get("home"), f"{context}.teams.home")
    away = _require_mapping(teams.get("away"), f"{context}.teams.away")
    home_team = _require_mapping(home.get("team"), f"{context}.teams.home.team")
    away_team = _require_mapping(away.get("team"), f"{context}.teams.away.team")
    venue = _require_mapping(game.get("venue"), f"{context}.venue")
    status = _require_mapping(game.get("status"), f"{context}.status")
    detailed = status.get("detailedState")
    game_datetime = game.get("gameDate")
    return ScheduledGame(
        game_pk=_require_int(game.get("gamePk"), f"{context}.gamePk"),
        official_date=_require_str(game.get("officialDate"), f"{context}.officialDate"),
        game_datetime_utc=game_datetime if isinstance(game_datetime, str) else "",
        status=detailed if isinstance(detailed, str) and detailed else "Unknown",
        venue_id=_require_int(venue.get("id"), f"{context}.venue.id"),
        venue_name=_require_str(venue.get("name"), f"{context}.venue.name"),
        home_team=_require_str(home_team.get("name"), f"{context}.teams.home.team.name"),
        away_team=_require_str(away_team.get("name"), f"{context}.teams.away.team.name"),
        home_probable=_probable(home, f"{context}.teams.home"),
        away_probable=_probable(away, f"{context}.teams.away"),
    )


def _parse_batting_order(team_block: Any, context: str) -> tuple[int, ...]:
    block = _require_mapping(team_block, context)
    raw = block.get("battingOrder")
    if not isinstance(raw, list):
        # Orders appear once posted; before that the key is absent or empty.
        return ()
    return tuple(_require_int(player_id, f"{context}.battingOrder") for player_id in raw)


def _side_code(person: dict[str, Any], key: str) -> str:
    block = person.get(key)
    if isinstance(block, dict):
        code = block.get("code")
        if isinstance(code, str):
            return code.strip()
    return ""


def _season_line(
    person: dict[str, Any],
    group: str,
    context: str,
) -> tuple[int, str, dict[str, Any]]:
    player_id = _require_int(person.get("id"), f"{context}.id")
    name = person.get("fullName")
    full_name = name if isinstance(name, str) and name else ""
    stats_blocks = person.get("stats")
    if not isinstance(stats_blocks, list):
        return (player_id, full_name, {})
    for block in stats_blocks:
        block_map = _require_mapping(block, f"{context}.stats[]")
        group_map = block_map.get("group")
        if isinstance(group_map, dict) and group_map.get("displayName") == group:
            splits = block_map.get("splits")
            if not isinstance(splits, list) or not splits:
                return (player_id, full_name, {})
            first = _require_mapping(splits[0], f"{context}.stats[].splits[0]")
            stat = first.get("stat")
            if not isinstance(stat, dict):
                return (player_id, full_name, {})
            return (player_id, full_name, stat)
    return (player_id, full_name, {})


class MlbStatsApi:
    """Reads the Stats API through an injected, host-pinned transport."""

    __slots__ = ("_transport",)

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def _get_json(self, url: str, context: str) -> Any | FetchFailure:
        try:
            response = get_with_retry(self._transport, url, _HEADERS)
        except TransportError as exc:
            return FetchFailure(f"{context}: transport failed ({exc})")
        if response.status != 200:
            return FetchFailure(f"{context}: HTTP {response.status}")
        try:
            return _parse_json(response.body, context)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))

    def fetch_slate(self, date_mmddyyyy: str) -> Slate | FetchFailure:
        """The day's schedule with venues, statuses and probable pitchers.

        ``date_mmddyyyy`` is the Stats API's own format (``"08/20/2026"``);
        the caller derives it from the injected clock, never this module.
        """
        parsed = self._get_json(_SCHEDULE_URL.format(date=date_mmddyyyy), "slate")
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            root = _require_mapping(parsed, "slate")
            dates = _require_list(root.get("dates"), "slate.dates")
            games: list[ScheduledGame] = []
            official_date = date_mmddyyyy
            for index, date_block in enumerate(dates):
                block = _require_mapping(date_block, f"slate.dates[{index}]")
                official_date = _require_str(block.get("date"), f"slate.dates[{index}].date")
                raw_games = _require_list(block.get("games"), f"slate.dates[{index}].games")
                for game_index, raw_game in enumerate(raw_games):
                    games.append(_parse_game(raw_game, f"slate.dates[{index}].games[{game_index}]"))
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return Slate(official_date=official_date, games=tuple(games))

    def fetch_batting_orders(self, game_pk: int) -> BattingOrders | FetchFailure:
        """Posted batting orders for one game; empty tuples when not yet posted."""
        context = f"boxscore[{game_pk}]"
        parsed = self._get_json(_BOXSCORE_URL.format(game_pk=game_pk), context)
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            root = _require_mapping(parsed, context)
            teams = _require_mapping(root.get("teams"), f"{context}.teams")
            home = _parse_batting_order(teams.get("home"), f"{context}.teams.home")
            away = _parse_batting_order(teams.get("away"), f"{context}.teams.away")
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return BattingOrders(game_pk=game_pk, home=home, away=away)

    def fetch_season_hitting(
        self, player_ids: tuple[int, ...]
    ) -> dict[int, SeasonHittingLine] | FetchFailure:
        """Season hitting counts for the given players, keyed by player id."""
        context = "season-hitting"
        parsed = self._get_json(
            _SEASON_STATS_URL.format(ids=",".join(str(i) for i in player_ids), group="hitting"),
            context,
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            root = _require_mapping(parsed, context)
            people = _require_list(root.get("people"), f"{context}.people")
            lines: dict[int, SeasonHittingLine] = {}
            for index, raw_person in enumerate(people):
                person = _require_mapping(raw_person, f"{context}.people[{index}]")
                player_id, full_name, stat = _season_line(
                    person, "hitting", f"{context}.people[{index}]"
                )
                if not stat:
                    continue  # no season split: the assembly layer marks absence
                lines[player_id] = SeasonHittingLine(
                    player_id=player_id,
                    full_name=full_name,
                    bats=_side_code(person, "batSide"),
                    games=_optional_int(stat, "gamesPlayed", context) or 0,
                    plate_appearances=_optional_int(stat, "plateAppearances", context) or 0,
                    at_bats=_optional_int(stat, "atBats", context) or 0,
                    hits=_optional_int(stat, "hits", context) or 0,
                    home_runs=_optional_int(stat, "homeRuns", context) or 0,
                    strikeouts=_optional_int(stat, "strikeOuts", context) or 0,
                    total_bases=_optional_int(stat, "totalBases", context) or 0,
                    sacrifice_flies=_optional_int(stat, "sacFlies", context) or 0,
                )
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return lines

    def fetch_recent_game_logs(
        self, player_ids: tuple[int, ...], start_mmddyyyy: str, end_mmddyyyy: str
    ) -> dict[int, tuple[GameLogEntry, ...]] | FetchFailure:
        """Recent hitting game logs for the given players, keyed by player id.

        Only completed games appear — an in-progress game is simply absent,
        which is exactly the semantics the money tag wants (D-100). Players
        with no appearances in the range are absent from the mapping.
        """
        context = "game-logs"
        parsed = self._get_json(
            _GAME_LOGS_URL.format(
                ids=",".join(str(i) for i in player_ids),
                start=start_mmddyyyy,
                end=end_mmddyyyy,
            ),
            context,
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            root = _require_mapping(parsed, context)
            people = _require_list(root.get("people"), f"{context}.people")
            logs: dict[int, tuple[GameLogEntry, ...]] = {}
            for index, raw_person in enumerate(people):
                person_context = f"{context}.people[{index}]"
                person = _require_mapping(raw_person, person_context)
                player_id = _require_int(person.get("id"), f"{person_context}.id")
                entries: list[GameLogEntry] = []
                for raw_block in person.get("stats", []):
                    block = _require_mapping(raw_block, f"{person_context}.stats")
                    for raw_split in block.get("splits", []):
                        split = _require_mapping(raw_split, f"{person_context}.splits")
                        # Season-total splits carry no date; only dated,
                        # gamed rows are game-log lines.
                        if "date" not in split or "game" not in split:
                            continue
                        stat = _require_mapping(split.get("stat"), f"{person_context}.splits.stat")
                        game = _require_mapping(split.get("game"), f"{person_context}.splits.game")
                        entries.append(
                            GameLogEntry(
                                date=_require_str(split.get("date"), person_context),
                                game_pk=_require_int(
                                    game.get("gamePk"), f"{person_context}.splits.game.gamePk"
                                ),
                                home_runs=_optional_int(stat, "homeRuns", context) or 0,
                                plate_appearances=(
                                    _optional_int(stat, "plateAppearances", context) or 0
                                ),
                            )
                        )
                if entries:
                    entries.sort(key=lambda entry: (entry.date, entry.game_pk))
                    logs[player_id] = tuple(entries)
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return logs

    def fetch_season_pitching(
        self, player_ids: tuple[int, ...]
    ) -> dict[int, SeasonPitchingLine] | FetchFailure:
        """Season pitching lines for the given players, keyed by player id."""
        context = "season-pitching"
        parsed = self._get_json(
            _SEASON_STATS_URL.format(ids=",".join(str(i) for i in player_ids), group="pitching"),
            context,
        )
        if isinstance(parsed, FetchFailure):
            return parsed
        try:
            root = _require_mapping(parsed, context)
            people = _require_list(root.get("people"), f"{context}.people")
            lines: dict[int, SeasonPitchingLine] = {}
            for index, raw_person in enumerate(people):
                person = _require_mapping(raw_person, f"{context}.people[{index}]")
                player_id, full_name, stat = _season_line(
                    person, "pitching", f"{context}.people[{index}]"
                )
                if not stat:
                    continue
                era = stat.get("era")
                whip = stat.get("whip")
                innings = stat.get("inningsPitched")
                lines[player_id] = SeasonPitchingLine(
                    player_id=player_id,
                    full_name=full_name,
                    throws=_side_code(person, "pitchHand"),
                    games_started=_optional_int(stat, "gamesStarted", context) or 0,
                    innings_pitched=innings if isinstance(innings, str) else "",
                    era=era if isinstance(era, str) else "",
                    whip=whip if isinstance(whip, str) else "",
                    strikeouts=_optional_int(stat, "strikeOuts", context) or 0,
                    batters_faced=_optional_int(stat, "battersFaced", context) or 0,
                    home_runs=_optional_int(stat, "homeRuns", context) or 0,
                )
        except PayloadMalformedError as exc:
            return FetchFailure(str(exc))
        return lines
