"""Form aggregation and the per-metric L7/L14 window resolution (D-068)."""

from __future__ import annotations

from decimal import Decimal

from greenmachine.live.form import (
    MIN_BBE_FORM,
    aggregate_form,
    resolve_form_section,
)
from greenmachine.live.savant import BatTrackingRow, PitchEvent


def _event(
    *,
    launch_speed_angle: int | None = None,
    launch_speed: str | None = None,
    launch_angle: str | None = None,
    bb_type: str = "",
    hc_x: str | None = None,
    hc_y: str | None = None,
    batter_side: str = "R",
    event: str = "",
    woba_value: str | None = None,
    woba_denom: str | None = None,
) -> PitchEvent:
    return PitchEvent(
        game_pk=1,
        game_date="2026-08-20",
        batter_id=101,
        pitcher_id=201,
        batter_side=batter_side,
        pitcher_throws="R",
        pitch_type="FF",
        event=event,
        description="",
        bb_type=bb_type,
        launch_speed=Decimal(launch_speed) if launch_speed is not None else None,
        launch_angle=Decimal(launch_angle) if launch_angle is not None else None,
        launch_speed_angle=launch_speed_angle,
        hc_x=Decimal(hc_x) if hc_x is not None else None,
        hc_y=Decimal(hc_y) if hc_y is not None else None,
        estimated_woba=None,
        woba_value=Decimal(woba_value) if woba_value is not None else None,
        woba_denom=Decimal(woba_denom) if woba_denom is not None else None,
    )


def _tracking(
    player_id: int, side: str, bat_speed: str, attack: str, ideal: str, swings: int
) -> BatTrackingRow:
    return BatTrackingRow(
        player_id=player_id,
        side=side,
        avg_bat_speed=Decimal(bat_speed),
        attack_angle=Decimal(attack),
        ideal_attack_angle_share=Decimal(ideal),
        competitive_swings=swings,
    )


def test_classified_contact_counts_as_a_batted_ball_event_and_fouls_do_not() -> None:
    metrics = aggregate_form(
        (
            _event(launch_speed_angle=6, launch_speed="108", launch_angle="28"),
            _event(launch_speed_angle=4, launch_speed="90", launch_angle="10"),
            _event(),  # a foul: unclassified, excluded from every denominator
        )
    )
    assert metrics.batted_ball_events == 2
    assert metrics.barrels == 1
    assert metrics.barrel_pct == Decimal("50")
    assert metrics.hard_hit_pct == Decimal("50")


def test_pull_is_signed_by_batter_side_and_unmeasurable_contacts_drop_out() -> None:
    pulled_righty = _event(
        launch_speed_angle=4, bb_type="fly_ball", hc_x="160", hc_y="160", batter_side="R"
    )
    opposite_righty = _event(
        launch_speed_angle=4, bb_type="fly_ball", hc_x="90", hc_y="160", batter_side="R"
    )
    unmeasurable = _event(launch_speed_angle=4, bb_type="fly_ball")
    metrics = aggregate_form((pulled_righty, opposite_righty, unmeasurable))
    assert metrics.air_balls == 2  # the unmeasurable contact leaves both counts
    assert metrics.pull_air_balls == 1
    assert metrics.pull_air_pct == Decimal("50")


def test_empty_windows_aggregate_to_nothing_without_error() -> None:
    metrics = aggregate_form(())
    assert metrics.batted_ball_events == 0
    assert metrics.barrel_pct is None


def test_each_metric_prefers_the_short_window_independently() -> None:
    recent = aggregate_form(
        tuple(_event(launch_speed_angle=6, launch_speed="100") for _ in range(MIN_BBE_FORM))
    )
    extended = aggregate_form(
        tuple(_event(launch_speed_angle=1, launch_speed="80") for _ in range(MIN_BBE_FORM))
    )
    section = resolve_form_section(recent, extended, (), ())
    assert section.barrel_pct.window_days == 7
    assert section.barrel_pct.value == Decimal("100")
    assert section.barrel_pct.sufficient


def test_a_metric_with_an_empty_short_window_falls_back_to_the_long_one() -> None:
    recent = aggregate_form(())
    extended = aggregate_form(
        tuple(_event(launch_speed_angle=6, launch_speed="100") for _ in range(MIN_BBE_FORM))
    )
    section = resolve_form_section(recent, extended, (), ())
    assert section.barrel_pct.window_days == 14
    assert section.barrel_pct.sufficient


def test_below_floor_samples_stay_visible_and_marked_insufficient() -> None:
    recent = aggregate_form((_event(launch_speed_angle=6, launch_speed="100"),))
    section = resolve_form_section(recent, aggregate_form(()), (), ())
    assert section.barrel_pct.value == Decimal("100")
    assert section.barrel_pct.sample == 1
    assert not section.barrel_pct.sufficient


def test_tracking_metrics_are_swing_weighted_across_sides() -> None:
    rows = (
        _tracking(101, "R", "70", "10", "0.5", 300),
        _tracking(101, "L", "80", "20", "0.9", 100),
    )
    section = resolve_form_section(aggregate_form(()), aggregate_form(()), rows, ())
    # (70*300 + 80*100) / 400 = 72.5 mph; ideal share (0.5*300+0.9*100)/400 = 0.6
    assert section.bat_speed_mph.value == Decimal("72.5")
    assert section.ideal_attack_angle_pct.value == Decimal("60")
    assert section.bat_speed_mph.window_days == 7
