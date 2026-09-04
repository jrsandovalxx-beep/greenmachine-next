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
# approved and D-176/D-183 shipped. String-compared: no float drift.
APPROVED_TABLES: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "exit_velocity": (
        "higher_is_better",
        [
            ("0", "86", "0"),
            ("86", "88", "0.25"),
            ("88", "89.5", "0.45"),
            ("89.5", "91", "0.65"),
            ("91", "92", "0.8"),
            ("92", "93", "0.9"),
            ("93", "130", "1"),
        ],
    ),
    "barrel_pct": (
        "higher_is_better",
        [
            ("0", "5", "0"),
            ("5", "7", "0.25"),
            ("7", "9", "0.5"),
            ("9", "11", "0.7"),
            ("11", "13", "0.85"),
            ("13", "100", "1"),
        ],
    ),
    "hard_hit_pct": (
        "higher_is_better",
        [
            ("0", "35", "0"),
            ("35", "40", "0.25"),
            ("40", "43", "0.5"),
            ("43", "46", "0.7"),
            ("46", "50", "0.85"),
            ("50", "100", "1"),
        ],
    ),
    "bat_speed": (
        "higher_is_better",
        [("0", "69", "0"), ("69", "70.5", "0.2"), ("70.5", "72", "0.4"), ("72", "130", "0.6")],
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
            ("0", "30", "0.5"),
            ("30", "32", "1"),
            ("32", "35", "1.5"),
            ("35", "45", "2"),
            ("45", "50", "1.5"),
            ("50", "55", "1"),
            ("55", "60", "0.5"),
            ("60", "100", "0.25"),
        ],
    ),
}

# attack_angle_quality's approved ramp (D-175) on the published ideal-rate
# measurement; the dormant proxy block keeps its own table (Q21 open).
APPROVED_ATTACK_ANGLE = [
    ("0", "38", "0"),
    ("38", "42", "0.2"),
    ("42", "46", "0.35"),
    ("46", "52", "0.5"),
    ("52", "58", "0.6"),
    ("58", "100", "0.7"),
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
        ("60", "100", "0.7"),
    ]


def test_the_slow_fastball_edge_bonus_is_wired_to_pitch_mix_pressure() -> None:
    """D-180's bonus declaration rides the same file; pin it too."""
    config = load_config(PRODUCTION)
    component = next(c for c in config.components if c.component_id.value == "pitch_mix_pressure")

    assert [(b.bonus_id, str(b.points)) for b in component.bonuses] == [
        ("slow_fastball_edge", "0.2")
    ]
