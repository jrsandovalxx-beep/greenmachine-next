"""Form-section runner: the batter detail dialog body without the main page.

The main screen is the Xbox shell plus the live board (D-076); selection and
dialog surfaces are verified on their own — AppTest at the pinned runtime has
no row-selection API and no dialog driver (D-061's boundary). The card is a
real one, built through ``build_board``; its form section is swapped for a
fixed showcase covering D-068's cell states: one metric on its L14 fallback,
one present below its floor with the INSUFFICIENT marker, and one with no
observations at either reach. Run with: streamlit run this file.
"""

import sys
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit_app

from greenmachine.config.loader import load_config
from greenmachine.inputs.contract import Handedness, ParkFactor
from greenmachine.live.form import FormSection, FormValue
from greenmachine.live.mlb_api import (
    BattingOrders,
    FetchFailure,
    GameLogEntry,
    ProbablePitcher,
    ScheduledGame,
    SeasonHittingLine,
    SeasonPitchingLine,
    Slate,
)
from greenmachine.live.pipeline import BatterCard, GameCard, SlateBoard, build_board
from greenmachine.live.savant import ExpectedStatsRow, SprintSpeedRow, StatcastPitcherRow

SLATE_DATE = date(2026, 8, 20)
AS_OF = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)
BATTER_ID = 101
PITCHER_ID = 201

# The D-068 showcase: Pull Air % on its L14 fallback, IdealAtkAng% below the
# 25-swing floor with its exact sample and marker; the rest ordinary
# sufficient L7 values.
SHOWCASE_FORM = FormSection(
    barrel_pct=FormValue(value=Decimal("18.2"), sample=22, window_games=7, sufficient=True),
    exit_velocity=FormValue(value=Decimal("91.4"), sample=22, window_games=7, sufficient=True),
    hard_hit_pct=FormValue(value=Decimal("49.5"), sample=22, window_games=7, sufficient=True),
    pull_air_pct=FormValue(value=Decimal("41.7"), sample=18, window_games=14, sufficient=True),
    attack_angle_degrees=FormValue(
        value=Decimal("13.1"), sample=40, window_games=7, sufficient=True
    ),
    ideal_attack_angle_pct=FormValue(
        value=Decimal("58.0"), sample=9, window_games=14, sufficient=False
    ),
    bat_speed_mph=FormValue(value=Decimal("74.2"), sample=40, window_games=7, sufficient=True),
    # D-116: the pulled-barrels raw count with its BBE sample.
    pulled_barrels=FormValue(value=Decimal(2), sample=22, window_games=7, sufficient=True),
)


class _RunnerApi:
    def fetch_slate(self, date_mmddyyyy: str) -> Slate:
        return Slate(
            official_date="2026-08-20",
            games=(
                ScheduledGame(
                    game_pk=777001,
                    official_date="2026-08-20",
                    game_datetime_utc="2026-08-21T01:40:00Z",
                    status="Scheduled",
                    venue_id=15,
                    venue_name="Chase Field",
                    home_team="Arizona Diamondbacks",
                    away_team="Los Angeles Dodgers",
                    home_probable=ProbablePitcher(player_id=PITCHER_ID, full_name="Ace Righty"),
                    away_probable=None,
                ),
            ),
        )

    def fetch_batting_orders(self, game_pk: int) -> BattingOrders:
        return BattingOrders(game_pk=game_pk, home=(BATTER_ID,), away=(BATTER_ID,))

    def fetch_season_hitting(self, player_ids: tuple[int, ...]) -> dict[int, SeasonHittingLine]:
        return {
            BATTER_ID: SeasonHittingLine(
                player_id=BATTER_ID,
                full_name="Covered Batter",
                bats="L",
                games=120,
                plate_appearances=500,
                at_bats=440,
                hits=121,
                home_runs=33,
                strikeouts=130,
            )
        }

    def fetch_season_pitching(self, player_ids: tuple[int, ...]) -> dict[int, SeasonPitchingLine]:
        return {
            PITCHER_ID: SeasonPitchingLine(
                player_id=PITCHER_ID,
                full_name="Ace Righty",
                throws="R",
                games_started=25,
                innings_pitched="150.1",
                era="3.10",
                whip="1.05",
                strikeouts=190,
                batters_faced=620,
                home_runs=26,  # D-111 showcase: a 1.56 HR/9, over the green line
            )
        }

    def fetch_recent_game_logs(
        self, player_ids: tuple[int, ...], start: str, end: str
    ) -> dict[int, tuple[GameLogEntry, ...]]:
        return {}

    def fetch_recent_pitching_logs(self, player_ids: tuple[int, ...], start: str, end: str) -> dict:
        return {}


class _RunnerSavant:
    def fetch_pitch_arsenal(self, *, kind: str, year: int) -> tuple:
        return ()

    def fetch_statcast_batters(self, *, year: int, minimum: int = 0) -> dict:
        return {}

    def fetch_bat_tracking(self, *, year: int, minimum: int = 0, start: str = "", end: str = ""):
        return ()

    def fetch_expected_stats(self, *, year: int) -> dict:
        return {}

    def fetch_sprint_speed(self, *, year: int) -> dict:
        return {BATTER_ID: SprintSpeedRow(player_id=BATTER_ID, sprint_speed=Decimal("28.9"))}

    def fetch_squared_up(self, *, year: int, minimum: int = 0) -> dict:
        return {}

    def fetch_pitcher_expected_stats(self, *, year: int) -> dict:
        # D-111 showcase: the starter card's season row carries real-shaped
        # values — a 1.50 HR/9, so the ratified vulnerability green shows.
        return {
            PITCHER_ID: ExpectedStatsRow(
                player_id=PITCHER_ID,
                plate_appearances=620,
                balls_in_play=450,
                batting_average=Decimal("0.240"),
                slugging=Decimal("0.410"),
                woba=Decimal("0.320"),
                expected_batting_average=Decimal("0.250"),
                expected_slugging=Decimal("0.430"),
                xwoba=Decimal("0.297"),
            )
        }

    def fetch_statcast_pitchers(self, *, year: int, minimum: int = 0) -> dict:
        return {
            PITCHER_ID: StatcastPitcherRow(
                player_id=PITCHER_ID,
                batted_ball_events=450,
                avg_launch_angle=Decimal("12.9"),
                barrel_count=36,
                hard_hit_count=180,
            )
        }

    def fetch_batted_ball(self, *, year: int, minimum: int = 0) -> dict:
        return {}


def _runner_card() -> tuple[BatterCard, GameCard]:
    board = build_board(
        api=_RunnerApi(),  # type: ignore[arg-type]
        savant=_RunnerSavant(),  # type: ignore[arg-type]
        slate_date=SLATE_DATE,
        as_of=AS_OF,
        config=load_config(
            Path(__file__).resolve().parents[3] / "config" / "production" / "gm_hr_v1.yaml"
        ),
        fetch_day_events=lambda day: FetchFailure("runner: events not needed"),  # type: ignore[arg-type]
        temperature_for=lambda venue, at: None,  # type: ignore[arg-type]
        park_factors={
            15: {
                Handedness.LEFT: ParkFactor(
                    factor=Decimal("112"), handedness=Handedness.LEFT, plate_appearances=30000
                ),
                Handedness.RIGHT: ParkFactor(
                    factor=Decimal("98"), handedness=Handedness.RIGHT, plate_appearances=30000
                ),
            }
        },
    )
    assert isinstance(board, SlateBoard)
    return replace(board.games[0].home_batters[0], form=SHOWCASE_FORM), board.games[0]


streamlit_app._render_batter_detail(*_runner_card())
