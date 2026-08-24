"""The Stats API adapter against synthetic payloads and scripted transports."""

from __future__ import annotations

import json

from greenmachine.live.mlb_api import FetchFailure, MlbStatsApi
from greenmachine.live.transport import HttpResponse, TransportUnreachableError

_SLATE = {
    "dates": [
        {
            "date": "2026-08-20",
            "games": [
                {
                    "gamePk": 777001,
                    "officialDate": "2026-08-20",
                    "gameDate": "2026-08-20T23:05:00Z",
                    "status": {"detailedState": "Scheduled"},
                    "venue": {"id": 15, "name": "Chase Field"},
                    "teams": {
                        "home": {
                            "team": {"name": "Arizona Diamondbacks"},
                            "probablePitcher": {"id": 111, "fullName": "Ace Righty"},
                        },
                        "away": {"team": {"name": "Los Angeles Dodgers"}},
                    },
                },
                {
                    "gamePk": 777002,
                    "officialDate": "2026-08-20",
                    "status": {"detailedState": "Final"},
                    "venue": {"id": 4705, "name": "Truist Park"},
                    "teams": {
                        "home": {"team": {"name": "Atlanta Braves"}},
                        "away": {
                            "team": {"name": "New York Mets"},
                            "probablePitcher": {"id": 222, "fullName": "Southpaw"},
                        },
                    },
                },
            ],
        }
    ]
}

_BOXSCORE = {
    "teams": {
        "home": {"battingOrder": [101, 102, 103, 104, 105, 106, 107, 108, 109]},
        "away": {"battingOrder": []},
    }
}

_PEOPLE_HITTING = {
    "people": [
        {
            "id": 101,
            "fullName": "Slugger One",
            "batSide": {"code": "L"},
            "stats": [
                {
                    "group": {"displayName": "hitting"},
                    "splits": [
                        {
                            "stat": {
                                "gamesPlayed": 120,
                                "plateAppearances": 500,
                                "atBats": 440,
                                "hits": 121,
                                "homeRuns": 33,
                                "strikeOuts": 130,
                                "totalBases": 204,
                                "sacFlies": 4,
                            }
                        }
                    ],
                }
            ],
        },
        {"id": 102, "fullName": "No Split", "stats": []},
    ]
}

_PEOPLE_PITCHING = {
    "people": [
        {
            "id": 111,
            "fullName": "Ace Righty",
            "pitchHand": {"code": "R"},
            "stats": [
                {
                    "group": {"displayName": "pitching"},
                    "splits": [
                        {
                            "stat": {
                                "gamesStarted": 25,
                                "inningsPitched": "150.1",
                                "era": "3.10",
                                "whip": "1.05",
                                "strikeOuts": 190,
                                "battersFaced": 620,
                                "homeRuns": 20,
                            }
                        }
                    ],
                }
            ],
        }
    ]
}


class _FakeTransport:
    def __init__(self, payload: object, status: int = 200) -> None:
        self._payload = payload
        self._status = status
        self.requested_urls: list[str] = []

    def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.requested_urls.append(url)
        return HttpResponse(status=self._status, body=json.dumps(self._payload).encode())


def _api(payload: object, status: int = 200) -> MlbStatsApi:
    return MlbStatsApi(_FakeTransport(payload, status))


def test_slate_parses_games_probables_and_missing_probables() -> None:
    slate = _api(_SLATE).fetch_slate("08/20/2026")
    assert not isinstance(slate, FetchFailure)
    assert slate.official_date == "2026-08-20"
    assert len(slate.games) == 2
    first, second = slate.games
    assert first.game_pk == 777001
    assert first.game_datetime_utc == "2026-08-20T23:05:00Z"
    assert first.venue_id == 15
    assert first.home_team == "Arizona Diamondbacks"
    assert first.home_probable is not None and first.home_probable.player_id == 111
    assert first.away_probable is None
    assert second.status == "Final"
    assert second.game_datetime_utc == ""
    assert second.home_probable is None
    assert second.away_probable is not None and second.away_probable.player_id == 222


def test_slate_without_dates_is_an_empty_slate() -> None:
    slate = _api({"dates": []}).fetch_slate("08/20/2026")
    assert not isinstance(slate, FetchFailure)
    assert slate.games == ()


def test_boxscore_returns_posted_and_unposted_orders() -> None:
    orders = _api(_BOXSCORE).fetch_batting_orders(777001)
    assert not isinstance(orders, FetchFailure)
    assert orders.home == (101, 102, 103, 104, 105, 106, 107, 108, 109)
    assert orders.away == ()


def test_season_hitting_counts_and_bat_side_parse() -> None:
    lines = _api(_PEOPLE_HITTING).fetch_season_hitting((101, 102))
    assert not isinstance(lines, FetchFailure)
    line = lines[101]
    assert line.bats == "L"
    assert line.plate_appearances == 500
    assert line.home_runs == 33
    assert line.total_bases == 204
    # D-110: sacrifice flies join the parse — the BABIP denominator's SF term.
    assert line.sacrifice_flies == 4
    assert 102 not in lines  # no season split: the assembly layer marks absence


def test_season_pitching_line_and_throwing_hand_parse() -> None:
    lines = _api(_PEOPLE_PITCHING).fetch_season_pitching((111,))
    assert not isinstance(lines, FetchFailure)
    line = lines[111]
    assert line.throws == "R"
    assert line.innings_pitched == "150.1"
    assert line.era == "3.10"
    assert line.batters_faced == 620
    assert line.home_runs == 20  # D-111: the HR/9 numerator


def test_a_non_200_status_becomes_a_fetch_failure() -> None:
    failure = _api({}, status=500).fetch_slate("08/20/2026")
    assert isinstance(failure, FetchFailure)
    assert "HTTP 500" in failure.reason


def test_a_malformed_payload_becomes_a_fetch_failure() -> None:
    failure = _api({"dates": [{"date": "2026-08-20", "games": [{"gamePk": "oops"}]}]}).fetch_slate(
        "08/20/2026"
    )
    assert isinstance(failure, FetchFailure)


def test_a_transport_error_becomes_a_fetch_failure() -> None:
    class _Down:
        def get(self, url: str, headers: dict[str, str]) -> HttpResponse:
            raise TransportUnreachableError("no route")

    failure = MlbStatsApi(_Down()).fetch_slate("08/20/2026")
    assert isinstance(failure, FetchFailure)
    assert "transport failed" in failure.reason


def test_the_stats_host_is_the_only_host_the_adapter_asks_for() -> None:
    transport = _FakeTransport(_SLATE)
    MlbStatsApi(transport).fetch_slate("08/20/2026")
    assert all(url.startswith("https://statsapi.mlb.com/") for url in transport.requested_urls)


_PEOPLE_GAME_LOG = {
    "people": [
        {
            "id": 101,
            "fullName": "Slugger One",
            "stats": [
                {
                    "group": {"displayName": "hitting"},
                    "type": {"displayName": "gameLog"},
                    "splits": [
                        {
                            "date": "2026-08-18",
                            "game": {"gamePk": 777000},
                            "stat": {"plateAppearances": 4, "homeRuns": 1},
                        },
                        {
                            "date": "2026-08-20",
                            "game": {"gamePk": 777002},
                            "stat": {"plateAppearances": 5, "homeRuns": 0},
                        },
                        {
                            "date": "2026-08-20",
                            "game": {"gamePk": 777003},
                            "stat": {"plateAppearances": 4, "homeRuns": 1},
                        },
                    ],
                },
                {
                    "group": {"displayName": "hitting"},
                    "type": {"displayName": "season"},
                    "splits": [{"stat": {"plateAppearances": 500, "homeRuns": 33}}],
                },
            ],
        },
        {"id": 102, "fullName": "No Games", "stats": []},
    ]
}


def test_game_logs_parse_dated_rows_and_skip_season_totals() -> None:
    """D-100: only dated, gamed splits are game-log lines; the season-total
    split riding the same response is not one. Entries sort by date then
    game, so a doubleheader keeps both games in order."""
    logs = _api(_PEOPLE_GAME_LOG).fetch_recent_game_logs((101, 102), "08/15/2026", "08/22/2026")
    assert not isinstance(logs, FetchFailure)
    assert 102 not in logs  # no appearances in the range: absent, not empty
    entries = logs[101]
    assert [(entry.date, entry.game_pk) for entry in entries] == [
        ("2026-08-18", 777000),
        ("2026-08-20", 777002),
        ("2026-08-20", 777003),
    ]
    first, _, third = entries
    assert (first.home_runs, first.plate_appearances) == (1, 4)
    assert (third.home_runs, third.plate_appearances) == (1, 4)


def test_game_logs_missing_count_fields_read_as_zero() -> None:
    payload = {
        "people": [
            {
                "id": 101,
                "stats": [
                    {
                        "splits": [
                            {
                                "date": "2026-08-20",
                                "game": {"gamePk": 777001},
                                "stat": {"plateAppearances": 2},
                            }
                        ]
                    }
                ],
            }
        ]
    }
    logs = _api(payload).fetch_recent_game_logs((101,), "08/20/2026", "08/20/2026")
    assert not isinstance(logs, FetchFailure)
    entry = logs[101][0]
    assert entry.home_runs == 0
    assert entry.plate_appearances == 2


def test_game_logs_malformed_split_is_a_fetch_failure() -> None:
    payload = {
        "people": [
            {
                "id": 101,
                "stats": [{"splits": [{"date": "2026-08-20", "game": {"gamePk": "oops"}}]}],
            }
        ]
    }
    failure = _api(payload).fetch_recent_game_logs((101,), "08/20/2026", "08/20/2026")
    assert isinstance(failure, FetchFailure)
