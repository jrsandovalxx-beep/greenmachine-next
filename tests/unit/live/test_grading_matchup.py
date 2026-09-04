"""The matchup derivations (D-178): usage-weighted ISO and put-away ISO.

D-175's measurement run (615,117 pitches; season-long cells and a
no-look-ahead pair-level check) found the matchup home-run signal is the
batter's PRODUCTION against the pitch — ISO — not the old beats-league
share and not whiff suppression (suppression marked the low-HR group).
These tests pin the derivations to that ruling: the percent-scale ISO
value, the usage weighting, the unreadable-cell skip, the put-away
pitch selection, and the K%-pitch fallback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import synthetic_records
from gm041_engine_snapshots import engine_snapshot

from greenmachine.config import load_config
from greenmachine.domain import (
    ComponentId,
    MetricObservation,
    MissingObservation,
    MissingReason,
)
from greenmachine.evaluation import deserialize_record, serialize_record
from greenmachine.live import grading
from greenmachine.live.grading import (
    BatterPitchLine,
    MatchupInput,
    PitchMixRow,
    derive_pitch_mix_pressure,
    derive_put_away_exploitation,
)
from greenmachine.live.savant import PitchEvent


def _pitch_row(
    pitch_type: str,
    *,
    usage: str,
    pitches: int = 400,
    put_away: str | None = None,
    strikeout: str | None = None,
) -> PitchMixRow:
    return PitchMixRow(
        pitch_type=pitch_type,
        pitch_name=pitch_type,
        pitches=pitches,
        usage_share=Decimal(usage),
        put_away_share=Decimal(put_away) if put_away is not None else None,
        strikeout_share=Decimal(strikeout) if strikeout is not None else None,
    )


def _batter_line(
    pitch_type: str,
    *,
    iso: str | None,
    pitches: int = 120,
) -> BatterPitchLine:
    return BatterPitchLine(
        pitch_type=pitch_type,
        pitches=pitches,
        expected_woba=None,
        whiff_share=None,
        iso=Decimal(iso) if iso is not None else None,
    )


def _matchup(
    pitcher_rows: tuple[PitchMixRow, ...],
    batter_rows: tuple[BatterPitchLine, ...],
) -> MatchupInput:
    return MatchupInput(pitcher_rows=pitcher_rows, batter_rows=batter_rows, league={})


def test_pitch_mix_pressure_is_the_usage_weighted_iso_on_the_percent_scale() -> None:
    matchup = _matchup(
        (
            _pitch_row("FF", usage="0.6"),
            _pitch_row("SL", usage="0.3"),
            _pitch_row("CH", usage="0.1"),  # below the qualifying usage share
        ),
        (
            _batter_line("FF", iso="0.2"),
            _batter_line("SL", iso="0.1"),
            _batter_line("CH", iso="0.9"),  # never counted: not qualifying
        ),
    )
    derived = derive_pitch_mix_pressure(matchup)
    assert derived.reason is None
    # (0.6 * 0.2 + 0.3 * 0.1) / 0.9 = 0.1666... * 100
    assert derived.value is not None
    assert abs(float(derived.value) - 16.6666667) < 1e-6
    assert derived.sample == 240


def test_pitch_mix_pressure_skips_pitch_types_the_batter_side_cannot_read() -> None:
    matchup = _matchup(
        (_pitch_row("FF", usage="0.5"), _pitch_row("SL", usage="0.5")),
        (_batter_line("FF", iso="0.2"),),  # no SL line at all
    )
    derived = derive_pitch_mix_pressure(matchup)
    assert derived.value == Decimal("20")
    assert derived.sample == 120


def test_pitch_mix_pressure_without_any_readable_cell_is_missing() -> None:
    matchup = _matchup(
        (_pitch_row("FF", usage="0.6"),),
        (_batter_line("FF", iso=None),),
    )
    derived = derive_pitch_mix_pressure(matchup)
    assert derived.value is None
    assert derived.reason is MissingReason.NO_EVENTS_IN_WINDOW


def test_put_away_reads_the_top_put_away_share_pitch() -> None:
    matchup = _matchup(
        (
            _pitch_row("FF", usage="0.5", put_away="0.2", strikeout="0.3"),
            _pitch_row("SL", usage="0.5", put_away="0.45", strikeout="0.1"),
        ),
        (_batter_line("FF", iso="0.3"), _batter_line("SL", iso="0.12")),
    )
    derived = derive_put_away_exploitation(matchup)
    assert derived.value == Decimal("12")
    assert derived.sample == 120


def test_put_away_falls_back_to_the_top_strikeout_share_pitch() -> None:
    """D-175's K%-pitch fallback: no row carries a put-away share."""
    matchup = _matchup(
        (
            _pitch_row("FF", usage="0.5", strikeout="0.1"),
            _pitch_row("CU", usage="0.5", strikeout="0.35"),
        ),
        (_batter_line("FF", iso="0.3"), _batter_line("CU", iso="0.18")),
    )
    derived = derive_put_away_exploitation(matchup)
    assert derived.value == Decimal("18")


def test_put_away_walks_past_a_pitch_the_batter_never_saw() -> None:
    matchup = _matchup(
        (
            _pitch_row("SL", usage="0.5", put_away="0.45"),
            _pitch_row("FF", usage="0.5", put_away="0.2"),
        ),
        (_batter_line("FF", iso="0.25"),),
    )
    derived = derive_put_away_exploitation(matchup)
    assert derived.value == Decimal("25")


def test_put_away_without_any_batter_line_is_missing() -> None:
    matchup = _matchup(
        (_pitch_row("FF", usage="0.6", put_away="0.4"),),
        (),
    )
    derived = derive_put_away_exploitation(matchup)
    assert derived.value is None
    assert derived.reason is MissingReason.NO_EVENTS_IN_WINDOW


def test_thin_sample_iso_above_one_is_reported_not_clamped() -> None:
    """D-179: ISO's ceiling is 4.000 (a homer in every at-bat against the
    pitch), so the percent scale runs past 100 — the derivation reports the
    value and the config domain (0-400) takes it; nothing clamps."""
    matchup = _matchup(
        (_pitch_row("FF", usage="0.6", put_away="0.4"),),
        (_batter_line("FF", iso="3.0"),),
    )
    derived = derive_put_away_exploitation(matchup)
    assert derived.value == Decimal("300")


def test_mix_pressure_reports_weighted_iso_above_one() -> None:
    matchup = _matchup(
        (_pitch_row("FF", usage="0.6"),),
        (_batter_line("FF", iso="1.4"),),
    )
    derived = derive_pitch_mix_pressure(matchup)
    assert derived.value == Decimal("140")


# --------------------------------------------------------------------------
# D-180 slow-fastball edge: the trigger behind the pitch_mix_pressure bonus
#
# The measurement run locked the exact trigger (D-178): the batter's season
# ISO against fastballs strictly under 92.5 mph minus his ISO against
# fastballs at or over 94.5 mph, each band at a 15-PA floor, must clear
# +.05 — and the starter's season fastball velocity must sit at or under
# 92.5 over at least 25 fastballs. Both legs measure or the edge is None.
# --------------------------------------------------------------------------

_EDGE_FIXTURE = (
    Path(__file__).resolve().parents[3] / "config" / "nonproduction" / "gm041_engine_synthetic.yaml"
)


def _fb_event(
    event: str = "",
    *,
    release_speed: str | None = "91.0",
    pitch_type: str = "FF",
) -> PitchEvent:
    return PitchEvent(
        game_pk=1,
        game_date="2026-08-20",
        batter_id=101,
        pitcher_id=201,
        batter_side="R",
        pitcher_throws="R",
        pitch_type=pitch_type,
        event=event,
        description="",
        bb_type="",
        launch_speed=None,
        launch_angle=None,
        launch_speed_angle=None,
        hc_x=None,
        hc_y=None,
        estimated_woba=None,
        woba_value=None,
        woba_denom=None,
        release_speed=Decimal(release_speed) if release_speed is not None else None,
    )


def _band(outcomes: list[str], speed: str) -> list[PitchEvent]:
    return [_fb_event(outcome, release_speed=speed) for outcome in outcomes]


def _qualifying_batter_events() -> list[PitchEvent]:
    # slow band ISO (12-3)/15 = .6; hard band ISO (4-1)/15 = .2; edge .4 > .05
    slow = _band(["home_run"] * 3 + ["field_out"] * 12, "90.5")
    hard = _band(["home_run"] + ["field_out"] * 14, "95.5")
    return slow + hard


def _starter_events(pitches: int = 25, speed: str = "91.0") -> list[PitchEvent]:
    return [_fb_event(release_speed=speed) for _ in range(pitches)]


def test_a_qualifying_edge_against_a_slow_starter_fires() -> None:
    assert grading.derive_slow_fastball_edge(_qualifying_batter_events(), _starter_events()) is True


def test_an_edge_below_the_trigger_does_not_fire() -> None:
    flat = _band(["home_run"] * 3 + ["field_out"] * 12, "90.5") + _band(
        ["home_run"] * 3 + ["field_out"] * 12, "95.5"
    )
    assert grading.derive_slow_fastball_edge(flat, _starter_events()) is False


def test_a_thin_batter_band_leaves_the_edge_unread() -> None:
    thin_slow = _band(["home_run"] * 3 + ["field_out"] * 11, "90.5")  # 14 PA, under the floor
    hard = _band(["home_run"] + ["field_out"] * 14, "95.5")
    assert grading.derive_slow_fastball_edge(thin_slow + hard, _starter_events()) is None


def test_a_fast_starter_does_not_fire() -> None:
    assert (
        grading.derive_slow_fastball_edge(
            _qualifying_batter_events(), _starter_events(speed="95.5")
        )
        is False
    )


def test_a_thin_starter_record_leaves_the_edge_unread() -> None:
    assert (
        grading.derive_slow_fastball_edge(_qualifying_batter_events(), _starter_events(24)) is None
    )


def test_a_starter_exactly_at_the_slow_edge_qualifies() -> None:
    """The starter leg is at-or-under; the batter band edge is strict."""
    assert (
        grading.derive_slow_fastball_edge(
            _qualifying_batter_events(), _starter_events(speed="92.5")
        )
        is True
    )


def test_pitches_without_a_recorded_speed_never_enter_either_leg() -> None:
    batter = _band(["home_run"] * 3 + ["field_out"] * 12, "90.5")
    batter += _band(["home_run"] + ["field_out"] * 14, "95.5")
    batter = [  # strip every recorded speed — both bands empty out
        _fb_event(event.event, release_speed=None) for event in batter
    ]
    assert grading.derive_slow_fastball_edge(batter, _starter_events()) is None
    assert (
        grading.derive_slow_fastball_edge(
            _qualifying_batter_events(),
            [_fb_event(release_speed=None) for _ in range(30)],
        )
        is None
    )


def test_non_fastball_pitch_types_are_ignored() -> None:
    batter = _band(["home_run"] * 3 + ["field_out"] * 12, "88.0")
    batter = [_fb_event(e.event, release_speed="88.0", pitch_type="SL") for e in batter]
    starter = [_fb_event(release_speed="88.0", pitch_type="SL") for _ in range(30)]
    assert grading.derive_slow_fastball_edge(batter, starter) is None


def test_the_dead_zone_between_the_bands_counts_on_neither_side() -> None:
    batter = _qualifying_batter_events() + _band(["field_out"] * 20, "93.5")
    assert grading.derive_slow_fastball_edge(batter, _starter_events()) is True


def test_the_slow_band_edge_is_strict_and_the_hard_edge_is_inclusive() -> None:
    # 92.5 exactly is NOT slow; the slow band empties out and the edge is unread.
    batter = _band(["home_run"] * 3 + ["field_out"] * 12, "92.5") + _band(
        ["home_run"] + ["field_out"] * 14,
        "94.5",  # 94.5 exactly IS hard
    )
    assert grading.derive_slow_fastball_edge(batter, _starter_events()) is None


def test_the_measurement_at_bat_accounting_is_pinned() -> None:
    """A sacrifice fly stays an at-bat; a walk and a sac bunt do not."""
    events = _band(["home_run"] * 3 + ["field_out"] * 11 + ["sac_fly", "walk", "sac_bunt"], "90.5")
    plate_appearances, iso = grading._band_iso(events)
    assert plate_appearances == 17
    assert iso == Decimal(9) / Decimal(15)  # AB = 17 - walk - sac_bunt; sac_fly stays

    no_sac_fly = _band(["home_run"] * 3 + ["field_out"] * 11 + ["walk", "sac_bunt"], "90.5")
    _, iso_without = grading._band_iso(no_sac_fly)
    assert iso_without == Decimal(9) / Decimal(14)


def _grading_input(edge: bool | None) -> grading.BatterGradingInput:
    matchup = MatchupInput(
        pitcher_rows=(_pitch_row("FF", usage="0.6"),),
        batter_rows=(_batter_line("FF", iso="0.2"),),
        league={},
    )
    return grading.BatterGradingInput(
        game=synthetic_records.game_context(),
        batter=synthetic_records.batter(),
        pitcher=synthetic_records.pitcher(),
        pitcher_throws="R",
        bats="R",
        tracking_sides=(),
        statcast=None,
        form=None,
        tracking_rows_present=False,
        matchup=matchup,
        home_run_factor=None,
        home_run_factor_plate_appearances=0,
        venue_roofed=False,
        temperature_fahrenheit=None,
        slow_fastball_edge=edge,
    )


def _pmp_observation(edge: bool | None) -> MetricObservation | MissingObservation:
    config = load_config(_EDGE_FIXTURE)
    observations = grading.build_batter_observations(
        _grading_input(edge),
        config=config,
        as_of=synthetic_records.AS_OF,
        season_start=datetime(2026, 3, 1, tzinfo=UTC),
        capture=synthetic_records.CAPTURE,
    )
    return next(
        observation
        for observation in observations
        if observation.component_id is ComponentId.PITCH_MIX_PRESSURE
    )


def test_a_measured_edge_attaches_the_qualifier_to_pitch_mix_pressure() -> None:
    observation = _pmp_observation(True)
    assert isinstance(observation, MetricObservation)
    assert observation.qualifiers == ("slow_fastball_edge",)


def test_no_edge_means_no_qualifier() -> None:
    for edge in (False, None):
        observation = _pmp_observation(edge)
        assert isinstance(observation, MetricObservation)
        assert observation.qualifiers == ()


def test_the_qualifier_survives_canonical_serialization() -> None:
    """The qualifier must round-trip byte-exact — a record that loses it
    would silently under-score on reload."""
    snapshot = engine_snapshot(qualifiers={ComponentId.PITCH_MIX_PRESSURE: ("slow_fastball_edge",)})
    restored = deserialize_record(serialize_record(snapshot))
    assert restored == snapshot
