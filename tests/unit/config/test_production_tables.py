"""The production bucket tables, pinned verbatim against the D-175 approvals.

D-176's merge shipped the band-direction enabler but silently dropped three
of the eight approved table rewrites (hard-hit, attack-angle, pull-air) — the
gate had nothing that pinned the production tables themselves, so the drop
passed green and the old cliffs stayed live for a day. This file is the pin:
every approved edge and point value, exactly as D-175 lists them. If a table
here moves, a D-entry must name it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from greenmachine.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION = REPO_ROOT / "config" / "production" / "gm_hr_v1.yaml"

# component -> (direction, [(lower, upper, points), ...]) exactly as D-175
# approved, D-176/D-183 shipped, and D-188 rescaled with the new component
# maxima. String-compared: no float drift.
APPROVED_TABLES: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "exit_velocity": (
        "higher_is_better",
        [
            ("0", "86", "0"),
            ("86", "88", "0.375"),
            ("88", "89.5", "0.675"),
            ("89.5", "91", "0.975"),
            ("91", "92", "1.2"),
            ("92", "93", "1.35"),
            ("93", "130", "1.5"),
        ],
    ),
    "barrel_pct": (
        "higher_is_better",
        [
            ("0", "5", "0"),
            ("5", "7", "0.5"),
            ("7", "9", "1"),
            ("9", "11", "1.4"),
            ("11", "13", "1.7"),
            ("13", "100", "2"),
        ],
    ),
    "hard_hit_pct": (
        "higher_is_better",
        [
            ("0", "35", "0"),
            ("35", "40", "0.125"),
            ("40", "43", "0.25"),
            ("43", "46", "0.35"),
            ("46", "50", "0.425"),
            ("50", "100", "0.5"),
        ],
    ),
    "bat_speed": (
        "higher_is_better",
        [("0", "69", "0"), ("69", "70.5", "0.1"), ("70.5", "72", "0.2"), ("72", "130", "0.3")],
    ),
    "park": (
        "higher_is_better",
        [
            ("0", "95", "0"),
            ("95", "100", "0.15"),
            ("100", "105", "0.3"),
            ("105", "110", "0.55"),
            ("110", "115", "0.75"),
            ("115", "120", "0.9"),
            ("120", "200", "1"),
        ],
    ),
    "weather": (
        "higher_is_better",
        [
            ("0", "50", "0"),
            ("50", "56", "0.2"),
            ("56", "62", "0.4"),
            ("62", "72", "0.55"),
            ("72", "80", "0.65"),
            ("80", "85", "0.8"),
            ("85", "90", "0.9"),
            ("90", "120", "1"),
        ],
    ),
    "pull_pct_air_balls": (
        "band",
        [
            ("0", "30", "0.25"),
            ("30", "32", "0.5"),
            ("32", "35", "0.75"),
            ("35", "45", "1"),
            ("45", "50", "0.75"),
            ("50", "55", "0.5"),
            ("55", "60", "0.25"),
            ("60", "100", "0.125"),
        ],
    ),
}

# attack_angle_quality's ramp (D-175, rescaled x10/7 by D-188) on the published
# ideal-rate measurement; the dormant proxy block keeps its own table (Q21 open).
APPROVED_ATTACK_ANGLE = [
    ("0", "38", "0"),
    ("38", "42", "0.29"),
    ("42", "46", "0.5"),
    ("46", "52", "0.71"),
    ("52", "58", "0.86"),
    ("58", "100", "1"),
]


def _table(component_id: str) -> list[tuple[str, str, str]]:
    config = load_config(PRODUCTION)
    component = next(c for c in config.components if c.component_id.value == component_id)
    profile = next(p for p in component.profiles if p.window_profile.value == "RECENT_7D")
    rows: list[tuple[str, str, str]] = []
    for scoring in profile.scoring:
        for bucket in scoring.buckets:  # type: ignore[union-attr]
            rows.append((str(bucket.lower), str(bucket.upper), str(bucket.points)))
    return rows


@pytest.mark.parametrize("component_id", sorted(APPROVED_TABLES))
def test_the_approved_bucket_table_is_shipped_verbatim(component_id: str) -> None:
    want_direction, want_table = APPROVED_TABLES[component_id]
    config = load_config(PRODUCTION)
    component = next(c for c in config.components if c.component_id.value == component_id)

    assert component.direction.value == want_direction
    assert _table(component_id) == want_table


def test_the_attack_angle_ideal_rate_ramp_is_shipped_verbatim() -> None:
    assert _table("attack_angle_quality") == [
        *APPROVED_ATTACK_ANGLE,
        ("0", "60", "0"),
        ("60", "100", "1"),
    ]


def test_the_slow_fastball_edge_bonus_is_wired_to_pitch_mix_pressure() -> None:
    """D-180's bonus declaration rides the same file; pin it too."""
    config = load_config(PRODUCTION)
    component = next(c for c in config.components if c.component_id.value == "pitch_mix_pressure")

    assert [(b.bonus_id, str(b.points)) for b in component.bonuses] == [
        ("slow_fastball_edge", "0.2")
    ]


# D-184: the ratified league-average priors and shrink strengths, measured
# over the 381-batter 2026 season board, 15k+ floored pair-days, the pinned
# park-factor cells, and 2,454 games of weather; D-188 rescaled the six
# reweighted components' priors in proportion to their new maxima.
# String-compared like the tables: a silent prior edit is a silent scoring change.
APPROVED_PRIORS: dict[str, tuple[str, int | None]] = {
    "exit_velocity": ("0.6", 15),
    "barrel_pct": ("0.86", 15),
    "hard_hit_pct": ("0.195", 15),
    "pitch_mix_pressure": ("0.56", None),
    "put_away_pitch_exploitation": ("0.61", None),
    "attack_angle_quality": ("0.63", 25),
    "bat_speed": ("0.125", 25),
    "pull_pct_air_balls": ("0.57", 5),
    "park": ("0.37", None),
    "weather": ("0.67", None),
}


@pytest.mark.parametrize("component_id", sorted(APPROVED_PRIORS))
def test_the_ratified_prior_and_shrink_strength_are_shipped_verbatim(
    component_id: str,
) -> None:
    want_prior, want_strength = APPROVED_PRIORS[component_id]
    config = load_config(PRODUCTION)
    component = next(c for c in config.components if c.component_id.value == component_id)

    assert component.prior_points is not None
    assert str(component.prior_points) == want_prior
    assert component.shrink_strength == want_strength


# D-188: the ratified HR-chance curve, re-measured over the 42-slate backtest
# under the D-188 weights (10,278 graded batter-days, 2026-07-26..2026-09-05,
# no look-ahead). The top anchor caps the tiny S sample (13 batters, 23.1%)
# at the 9-10 bin's read until the S sample grows. String-compared like the
# tables: a silent anchor edit is a silent display change.
APPROVED_HR_CHANCE: tuple[tuple[str, str], ...] = (
    ("1", "5.8"),
    ("2.5", "5.8"),
    ("3.5", "7.2"),
    ("4.5", "9.2"),
    ("5.5", "11.6"),
    ("6.5", "13.6"),
    ("7.5", "14.6"),
    ("8.5", "14.9"),
    ("9.5", "15.7"),
)


def test_the_ratified_hr_chance_curve_is_shipped_verbatim() -> None:
    config = load_config(PRODUCTION)

    assert config.hr_chance is not None
    assert [(str(a.score), str(a.chance)) for a in config.hr_chance] == list(APPROVED_HR_CHANCE)
