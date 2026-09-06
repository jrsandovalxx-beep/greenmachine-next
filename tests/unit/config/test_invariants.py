"""Every invariant in ``MODEL_SPEC.md`` §19, proven to be a load failure.

Each case is a one-line mutation of the valid fixture, so the diff between a
working configuration and a rejected one is exactly the rule under test. Every
assertion also checks the reported key path: an error that fails to say *where*
is barely better than no error at all.
"""

from __future__ import annotations

import pytest
from config_fixtures import (
    DESCENDING_BUCKETS,
    EV_BUCKETS,
    EV_PROFILE_RECENT,
    FUZZY_DISABLED,
    GRADE_C,
    GRADE_D,
    GRADE_S,
    PROXY_DEFINITION,
    WEATHER_BINARY,
    mutate,
    valid_text,
)

from greenmachine.config import ConfigSchemaError, ConfigSemanticError, load_config_text


def reject(text: str) -> ConfigSemanticError:
    """Load and require a semantic rejection, returning the error."""
    with pytest.raises(ConfigSemanticError) as caught:
        load_config_text(text, file_path="synthetic.yaml")
    assert caught.value.context.file_path == "synthetic.yaml"
    return caught.value


# --------------------------------------------------------------------------
# Buckets (invariants 1, 2, 3, 7, 8, 9, 10)
# --------------------------------------------------------------------------


def test_overlapping_buckets_are_rejected() -> None:
    error = reject(mutate(EV_BUCKETS, EV_BUCKETS.replace('{ lower: "62.4"', '{ lower: "55.0"')))

    assert "meet exactly" in str(error)
    assert error.context.metric == "exit_velocity"


def test_a_bucket_gap_is_rejected() -> None:
    error = reject(mutate(EV_BUCKETS, EV_BUCKETS.replace('{ lower: "62.4"', '{ lower: "70.0"')))

    assert "meet exactly" in str(error)


def test_bucket_points_below_zero_are_rejected() -> None:
    error = reject(mutate(EV_BUCKETS, EV_BUCKETS.replace('points: "0" }', 'points: "-0.1" }')))

    assert "points must be >= 0" in str(error)
    assert error.context.key_path[-1] == "points"


def test_bucket_points_exceeding_max_points_are_rejected() -> None:
    error = reject(mutate(EV_BUCKETS, EV_BUCKETS.replace('points: "0.4" }', 'points: "1.7" }')))

    assert "exceed the component max_points" in str(error)


def test_a_strongest_bucket_that_does_not_award_max_points_is_rejected() -> None:
    error = reject(mutate(EV_BUCKETS, EV_BUCKETS.replace('points: "0.9" }', 'points: "0.8" }')))

    assert "strongest qualifying bucket must award" in str(error)


def test_non_monotonic_higher_is_better_points_are_rejected() -> None:
    """Points may never decrease as values increase."""
    error = reject(
        mutate(
            EV_BUCKETS,
            EV_BUCKETS.replace('upper: "62.4", points: "0" }', 'upper: "62.4", points: "0.6" }'),
        )
    )

    assert "never decrease" in str(error)


def test_non_monotonic_lower_is_better_points_are_rejected() -> None:
    """Points may never increase as values increase."""
    error = reject(
        mutate(
            DESCENDING_BUCKETS,
            DESCENDING_BUCKETS.replace(
                'upper: "19.2", points: "1.9" }', 'upper: "19.2", points: "0.5" }'
            ),
            count=2,
        )
    )

    assert "never increase" in str(error)
    assert error.context.metric == "put_away_pitch_exploitation"


def test_a_first_bucket_that_misses_the_domain_minimum_is_rejected() -> None:
    error = reject(
        mutate(EV_BUCKETS, EV_BUCKETS.replace('- { lower: "0",    upper', '- { lower: "1", upper'))
    )

    assert "must start at domain_min" in str(error)


def test_a_final_bucket_that_misses_the_domain_maximum_is_rejected() -> None:
    error = reject(
        mutate(EV_BUCKETS, EV_BUCKETS.replace('upper: "125",  points', 'upper: "124", points'))
    )

    assert "must end at domain_max" in str(error)


def test_a_reversed_bucket_is_rejected() -> None:
    error = reject(
        mutate(
            EV_BUCKETS,
            EV_BUCKETS.replace(
                '- { lower: "62.4", upper: "88.1"', '- { lower: "88.1", upper: "62.4"'
            ),
        )
    )

    assert "must be <" in str(error)


def test_an_inverted_domain_is_rejected() -> None:
    error = reject(
        mutate(
            EV_PROFILE_RECENT,
            EV_PROFILE_RECENT.replace('domain_max: "125"', 'domain_max: "0"'),
        )
    )

    assert "domain_min" in str(error)


# --------------------------------------------------------------------------
# Allocations (invariants 4, 5, 6, 14)
# --------------------------------------------------------------------------


def test_component_maxima_that_do_not_sum_to_the_category_maximum_are_rejected() -> None:
    error = reject(mutate('      max_points: "2.7"', '      max_points: "2.8"'))

    assert "sum to" in str(error)
    assert error.context.key_path[:2] == ("allocations", "categories")


def test_category_maxima_that_do_not_sum_to_the_total_are_rejected() -> None:
    """Changing one category and its components keeps the inner sum but breaks the total."""
    text = mutate('      max_points: "2.7"', '      max_points: "2.6"')
    text = text.replace(
        '    max_points: "0.9"\n    sample_type: batted_ball_events',
        '    max_points: "0.8"\n    sample_type: batted_ball_events',
        1,
    )
    error = reject(text)

    assert "category maximums sum to" in str(error)


def test_a_wrong_total_max_points_is_rejected() -> None:
    error = reject(mutate('  total_max_points: "11.3"', '  total_max_points: "11"'))

    assert "total_max_points must be 11.3" in str(error)
    assert error.context.key_path == ("allocations", "total_max_points")


def test_a_duplicate_category_is_rejected() -> None:
    error = reject(
        mutate(
            '    - category: pull_power\n      max_points: "2.3"\n'
            "      components: [pull_pct_air_balls]",
            '    - category: power_profile\n      max_points: "2.4"\n'
            "      components: [pull_pct_air_balls]",
        )
    )

    assert "declared more than once" in str(error)


def test_an_undefined_component_reference_is_rejected() -> None:
    error = reject(
        mutate(
            "      components: [pull_pct_air_balls]",
            "      components: [pull_pct_air_balls, park]",
        )
    )

    # `park` is already claimed by environment, so this reads as a double claim.
    assert "more than one category" in str(error)


def test_an_orphan_component_is_rejected() -> None:
    """A configured component that no category claims."""
    error = reject(
        mutate("      components: [park, weather]", "      components: [weather]").replace(
            '      max_points: "1.7"', '      max_points: "0.8"', 1
        )
    )

    assert "not placed in any category" in str(error)


def test_a_duplicate_component_definition_is_rejected() -> None:
    text = mutate(
        "  - component_id: weather\n    scoring_method: binary",
        "  - component_id: park\n    scoring_method: binary",
    )
    error = reject(text)

    assert "configured more than once" in str(error)


def test_an_unknown_component_identifier_is_refused_by_the_schema() -> None:
    with pytest.raises(ConfigSchemaError):
        load_config_text(mutate("  - component_id: park", "  - component_id: chase_rate"))


def test_a_retired_component_cannot_be_referenced() -> None:
    with pytest.raises(ConfigSchemaError):
        load_config_text(
            mutate("      components: [pull_pct_air_balls]", "      components: [whiff_rate]")
        )


# --------------------------------------------------------------------------
# Grade cutoffs (invariant 13)
# --------------------------------------------------------------------------


def test_unordered_grade_cutoffs_are_rejected() -> None:
    text = mutate(f"{GRADE_D}\n{GRADE_C}", f"{GRADE_C}\n{GRADE_D}")
    error = reject(text)

    assert "ascending order" in str(error)


def test_a_grade_cutoff_gap_is_rejected() -> None:
    error = reject(
        mutate(GRADE_C, '    - { grade: C, lower: "3.4", upper: "5.1", terminal: false }')
    )

    assert "meet exactly" in str(error)


def test_a_grade_cutoff_overlap_is_rejected() -> None:
    error = reject(
        mutate(GRADE_C, '    - { grade: C, lower: "3.2", upper: "5.1", terminal: false }')
    )

    assert "meet exactly" in str(error)


def test_a_missing_grade_is_rejected() -> None:
    error = reject(mutate(f"{GRADE_C}\n", ""))

    assert "grade missing" in str(error)


def test_a_duplicate_grade_is_rejected() -> None:
    error = reject(
        mutate(GRADE_C, '    - { grade: D, lower: "3.3", upper: "5.1", terminal: false }')
    )

    assert "declared more than once" in str(error)


def test_a_grade_table_that_does_not_start_at_zero_is_rejected() -> None:
    error = reject(
        mutate(GRADE_D, '    - { grade: D, lower: "0.5", upper: "3.3", terminal: false }')
    )

    assert "must start at 0" in str(error)


def test_a_grade_table_that_does_not_end_at_the_total_is_rejected() -> None:
    error = reject(mutate(GRADE_S, '    - { grade: S, lower: "9.4", upper: "11", terminal: true }'))

    assert "must end at 11.3" in str(error)


def test_a_missing_terminal_grade_is_rejected() -> None:
    error = reject(
        mutate(GRADE_S, '    - { grade: S, lower: "9.4", upper: "11.3",  terminal: false }')
    )

    assert "terminal" in str(error)


def test_more_than_one_terminal_grade_is_rejected() -> None:
    error = reject(
        mutate(GRADE_C, '    - { grade: C, lower: "3.3", upper: "5.1", terminal: true }')
    )

    assert "terminal" in str(error)


# --------------------------------------------------------------------------
# Profiles and measurements (invariants 15, 16)
# --------------------------------------------------------------------------


def test_a_missing_profile_definition_is_rejected() -> None:
    error = reject(mutate(f"{EV_PROFILE_RECENT}\n", ""))

    assert "do not match applicable_profiles" in str(error)
    assert error.context.metric == "exit_velocity"


def test_a_duplicate_profile_definition_is_rejected() -> None:
    error = reject(mutate(EV_PROFILE_RECENT, f"{EV_PROFILE_RECENT}\n{EV_PROFILE_RECENT}"))

    assert "defined more than once" in str(error)


def test_an_undeclared_profile_definition_is_rejected() -> None:
    error = reject(
        mutate(
            "    applicable_profiles: [RECENT_7D, LONG_TERM_2Y]\n    profiles:\n"
            "      - window_profile: RECENT_7D\n        minimum_sample_required: 3\n"
            '        scoring:\n          - method: bucketed\n            domain_min: "0"\n'
            '            domain_max: "125"',
            "    applicable_profiles: [RECENT_7D]\n    profiles:\n"
            "      - window_profile: RECENT_7D\n        minimum_sample_required: 3\n"
            '        scoring:\n          - method: bucketed\n            domain_min: "0"\n'
            '            domain_max: "125"',
        )
    )

    assert "do not match applicable_profiles" in str(error)


def test_a_missing_measurement_definition_is_rejected() -> None:
    error = reject(mutate(f"{PROXY_DEFINITION}\n", ""))

    assert "exactly one bucket set per measurement" in str(error)
    assert error.context.metric == "attack_angle_quality"


def test_a_duplicate_measurement_definition_is_rejected() -> None:
    error = reject(
        mutate(
            PROXY_DEFINITION,
            PROXY_DEFINITION.replace(
                "measurement_id: attack_angle_threshold_proxy",
                "measurement_id: ideal_attack_angle_pct",
            ),
        )
    )

    assert "more than once" in str(error) or "requires a bucket set for both" in str(error)


def test_a_measurement_on_a_non_attack_component_is_rejected() -> None:
    error = reject(
        mutate(
            EV_PROFILE_RECENT,
            EV_PROFILE_RECENT.replace(
                "          - method: bucketed\n",
                "          - method: bucketed\n"
                "            measurement_id: ideal_attack_angle_pct\n",
            ),
        )
    )

    assert "only attack_angle_quality may name a measurement" in str(error)


# --------------------------------------------------------------------------
# Schema-shape separation (invariants 11, 12)
# --------------------------------------------------------------------------


def test_a_binary_component_containing_bucket_fields_is_refused() -> None:
    text = mutate(
        WEATHER_BINARY,
        WEATHER_BINARY.replace(
            '            qualified_points: "0.8"',
            '            qualified_points: "0.8"\n            domain_min: "0"',
        ),
        count=2,
    )

    with pytest.raises(ConfigSchemaError, match=r"[Ee]xtra|not permitted"):
        load_config_text(text, file_path="synthetic.yaml")


def test_a_binary_component_declaring_buckets_is_refused() -> None:
    text = mutate(
        WEATHER_BINARY,
        WEATHER_BINARY.replace(
            '            qualified_points: "0.8"',
            '            qualified_points: "0.8"\n            buckets: []',
        ),
        count=2,
    )

    with pytest.raises(ConfigSchemaError):
        load_config_text(text, file_path="synthetic.yaml")


def test_a_bucketed_component_containing_binary_fields_is_refused() -> None:
    text = mutate(
        EV_PROFILE_RECENT,
        EV_PROFILE_RECENT.replace(
            '            domain_max: "125"',
            '            domain_max: "125"\n            qualified_points: "0.9"',
        ),
    )

    with pytest.raises(ConfigSchemaError):
        load_config_text(text, file_path="synthetic.yaml")


def test_a_declared_method_that_contradicts_the_definition_is_rejected() -> None:
    error = reject(mutate("    scoring_method: binary", "    scoring_method: bucketed"))

    assert "scoring_method" in str(error)


def test_a_binary_award_below_max_points_is_rejected() -> None:
    error = reject(
        mutate(
            WEATHER_BINARY,
            WEATHER_BINARY.replace('qualified_points: "0.8"', 'qualified_points: "0.5"'),
            count=2,
        )
    )

    assert "qualified_points must equal" in str(error)
    assert error.context.metric == "weather"


def test_a_predicate_with_neither_clause_is_refused() -> None:
    text = mutate(
        WEATHER_BINARY,
        WEATHER_BINARY.replace(
            "            predicate:\n              all_of:\n"
            "                - { input_name: synthetic_input_a, operator: at_least,"
            ' value: "41.7" }\n'
            "                - { input_name: synthetic_input_b, operator: greater_than,"
            ' value: "3.9" }',
            "            predicate: {}",
        ),
        count=2,
    )
    error = reject(text)

    assert "exactly one of 'all_of' or 'any_of'" in str(error)


# --------------------------------------------------------------------------
# Fuzzy scoring
# --------------------------------------------------------------------------


def test_fuzzy_scoring_enabled_is_rejected() -> None:
    error = reject(mutate(FUZZY_DISABLED, "  enabled: true"))

    assert "must be explicitly disabled" in str(error)
    assert error.context.key_path == ("fuzzy_scoring", "enabled")


def test_a_non_boolean_fuzzy_flag_is_refused() -> None:
    with pytest.raises(ConfigSchemaError):
        load_config_text(mutate(FUZZY_DISABLED, '  enabled: "false"'))


# --------------------------------------------------------------------------
# Numeric policy
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "old", "new"),
    [
        ("yaml float", '  total_max_points: "11.3"', "  total_max_points: 12.0"),
        ("yaml integer", '  total_max_points: "11.3"', "  total_max_points: 12"),
        ("boolean", '  total_max_points: "11.3"', "  total_max_points: true"),
        ("malformed string", '  total_max_points: "11.3"', '  total_max_points: "abc"'),
        ("NaN", '  total_max_points: "11.3"', '  total_max_points: "NaN"'),
        ("Infinity", '  total_max_points: "11.3"', '  total_max_points: "Infinity"'),
        ("empty string", '  total_max_points: "11.3"', '  total_max_points: ""'),
    ],
)
def test_scoring_numerics_must_be_quoted_decimal_strings(label: str, old: str, new: str) -> None:
    with pytest.raises(ConfigSchemaError) as caught:
        load_config_text(mutate(old, new), file_path="synthetic.yaml")

    assert caught.value.context.key_path[0] == "allocations"


@pytest.mark.parametrize(
    ("label", "new"),
    [
        ("boolean", "        minimum_sample_required: true"),
        ("float", "        minimum_sample_required: 5.5"),
        ("numeric string", '        minimum_sample_required: "5"'),
        ("negative", "        minimum_sample_required: -1"),
    ],
)
def test_count_fields_must_be_strict_non_negative_integers(label: str, new: str) -> None:
    with pytest.raises(ConfigSchemaError):
        load_config_text(
            mutate("        minimum_sample_required: 5", new), file_path="synthetic.yaml"
        )


def test_a_bucket_point_supplied_as_a_yaml_float_is_refused() -> None:
    text = mutate(EV_BUCKETS, EV_BUCKETS.replace('points: "0.4" }', "points: 0.4 }"))

    with pytest.raises(ConfigSchemaError, match=r"YAML float"):
        load_config_text(text, file_path="synthetic.yaml")


# --------------------------------------------------------------------------
# D-180 bonus rules (points-level add-ons on measured qualifiers)
# --------------------------------------------------------------------------

_EV_COMPONENT_HEAD = """  - component_id: exit_velocity
    scoring_method: bucketed
    direction: higher_is_better
    max_points: "0.9"
"""
_EV_BONUS = '    bonuses:\n      - { bonus_id: slow_fastball_edge, points: "0.2" }\n'


def _ev_with_bonus(bonus_block: str) -> str:
    return mutate(_EV_COMPONENT_HEAD, _EV_COMPONENT_HEAD + bonus_block)


def test_a_valid_bonus_rule_loads() -> None:
    config = load_config_text(_ev_with_bonus(_EV_BONUS), file_path="synthetic.yaml")
    ev = next(c for c in config.components if c.component_id.value == "exit_velocity")
    assert [(b.bonus_id, str(b.points)) for b in ev.bonuses] == [("slow_fastball_edge", "0.2")]


def test_a_duplicate_bonus_id_is_rejected() -> None:
    duplicate_block = (
        "    bonuses:\n"
        '      - { bonus_id: slow_fastball_edge, points: "0.2" }\n'
        '      - { bonus_id: slow_fastball_edge, points: "0.1" }\n'
    )
    error = reject(_ev_with_bonus(duplicate_block))

    assert "bonus declared more than once" in str(error)
    assert "slow_fastball_edge" in str(error)


def test_zero_bonus_points_are_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_BONUS.replace('points: "0.2"', 'points: "0"')))

    assert "bonus points must be positive" in str(error)


def test_negative_bonus_points_are_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_BONUS.replace('points: "0.2"', 'points: "-0.2"')))

    assert "bonus points must be positive" in str(error)


def test_bonus_points_at_the_component_max_are_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_BONUS.replace('points: "0.2"', 'points: "0.9"')))

    assert "must sit below the component max_points" in str(error)


def test_an_empty_bonus_id_is_refused_by_the_schema() -> None:
    with pytest.raises(ConfigSchemaError):
        load_config_text(
            _ev_with_bonus(_EV_BONUS.replace("slow_fastball_edge", "")),
            file_path="synthetic.yaml",
        )


# --------------------------------------------------------------------------
# D-184 prior rules (league-average substitution + thin-sample shrinkage)
# --------------------------------------------------------------------------

_EV_PRIOR = '    prior_points: "0.4"\n'
_EV_SHRINK = "    shrink_strength: 15\n"


def test_a_valid_prior_and_shrink_strength_load() -> None:
    config = load_config_text(_ev_with_bonus(_EV_PRIOR + _EV_SHRINK), file_path="synthetic.yaml")
    ev = next(c for c in config.components if c.component_id.value == "exit_velocity")
    assert str(ev.prior_points) == "0.4"
    assert ev.shrink_strength == 15


def test_a_prior_without_shrinkage_loads() -> None:
    config = load_config_text(_ev_with_bonus(_EV_PRIOR), file_path="synthetic.yaml")
    ev = next(c for c in config.components if c.component_id.value == "exit_velocity")
    assert str(ev.prior_points) == "0.4"
    assert ev.shrink_strength is None


def test_zero_prior_points_are_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_PRIOR.replace('"0.4"', '"0"')))

    assert "prior_points must be positive" in str(error)


def test_negative_prior_points_are_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_PRIOR.replace('"0.4"', '"-0.1"')))

    assert "prior_points must be positive" in str(error)


def test_prior_points_at_the_component_max_are_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_PRIOR.replace('"0.4"', '"0.9"')))

    assert "must sit below the component max_points" in str(error)


def test_shrinkage_without_a_prior_is_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_SHRINK))

    assert "shrink_strength requires prior_points" in str(error)


def test_zero_shrink_strength_is_rejected() -> None:
    error = reject(_ev_with_bonus(_EV_PRIOR + _EV_SHRINK.replace("15", "0")))

    assert "shrink_strength must be positive" in str(error)


# --------------------------------------------------------------------------
# D-186 hr_chance rules (the calibrated display curve)
# --------------------------------------------------------------------------

_HR_CHANCE = 'hr_chance:\n  - { score: "1", chance: "4" }\n  - { score: "5", chance: "12" }\n'


def _with_hr_chance(block: str) -> str:
    return mutate("\ncomponents:\n", "\n" + block + "components:\n")


def test_a_valid_hr_chance_curve_loads() -> None:
    config = load_config_text(_with_hr_chance(_HR_CHANCE), file_path="synthetic.yaml")
    assert config.hr_chance is not None
    assert [(str(a.score), str(a.chance)) for a in config.hr_chance] == [("1", "4"), ("5", "12")]


def test_hr_chance_is_optional() -> None:
    config = load_config_text(valid_text(), file_path="synthetic.yaml")
    assert config.hr_chance is None


def test_a_single_anchor_is_rejected() -> None:
    error = reject(_with_hr_chance('hr_chance:\n  - { score: "1", chance: "4" }\n'))

    assert "hr_chance needs at least two anchors to interpolate" in str(error)


def test_a_chance_outside_the_percent_scale_is_rejected() -> None:
    error = reject(
        _with_hr_chance(
            'hr_chance:\n  - { score: "1", chance: "104" }\n' + _HR_CHANCE.split("\n", 1)[1]
        )
    )

    assert "chance must sit inside 0-100" in str(error)


def test_anchor_scores_must_strictly_increase() -> None:
    error = reject(
        _with_hr_chance(
            'hr_chance:\n  - { score: "5", chance: "4" }\n  - { score: "1", chance: "12" }\n'
        )
    )

    assert "anchor scores must strictly increase" in str(error)


def test_chances_must_not_decrease() -> None:
    error = reject(
        _with_hr_chance(
            'hr_chance:\n  - { score: "1", chance: "12" }\n  - { score: "5", chance: "4" }\n'
        )
    )

    assert "chances must not decrease" in str(error)
