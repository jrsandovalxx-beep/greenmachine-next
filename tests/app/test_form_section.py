"""GMF-007: the form section's cell rules, and the selection surface's render.

The frames are direct-tested here as ordinary code. The dialog itself sits
past AppTest's boundary at the pinned runtime — no row-selection API and no
dialog driver (D-061) — so the dialog body is exercised by
``tests/app/runners/run_form_section.py`` plus browser screenshots, and the
AppTest below only proves the board still renders with the selectable grids.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import streamlit_app
from streamlit.testing.v1 import AppTest
from test_live_board_render import _staged_app  # noqa: F401  (fixture import)

from greenmachine.live.form import FormSection, FormValue
from greenmachine.live.pipeline import SlateBoard

REPO_ROOT = Path(__file__).resolve().parents[2]
_APP_PATH = REPO_ROOT / "streamlit_app.py"
_TIMEOUT = 60


def _form(**overrides: FormValue) -> FormSection:
    """A FormSection that is present, L7, and sufficient on every metric,
    with per-metric overrides — the deviations are what each test reads."""
    sufficient = FormValue(value=Decimal("10"), sample=20, window_days=7, sufficient=True)
    return FormSection(
        barrel_pct=overrides.get("barrel_pct", sufficient),
        exit_velocity=overrides.get("exit_velocity", sufficient),
        hard_hit_pct=overrides.get("hard_hit_pct", sufficient),
        sweet_spot_pct=overrides.get("sweet_spot_pct", sufficient),
        pull_air_pct=overrides.get("pull_air_pct", sufficient),
        attack_angle_degrees=overrides.get("attack_angle_degrees", sufficient),
        ideal_attack_angle_pct=overrides.get("ideal_attack_angle_pct", sufficient),
        bat_speed_mph=overrides.get("bat_speed_mph", sufficient),
        oppo_air_pct=overrides.get("oppo_air_pct", sufficient),
        pulled_barrels=overrides.get(
            "pulled_barrels",
            FormValue(value=Decimal(2), sample=41, window_days=7, sufficient=True),
        ),
    )


def test_columns_are_the_d068_set_minus_xwoba_in_order() -> None:
    """D-102: xwOBA left the popup form grid; it stays on the Matchups main
    tables. D-109 amended the set: SwSp% — computed and graded from the
    start — is displayed, and Oppo Air % mirrors Pull Air %. D-116 adds
    the pulled-barrels raw count."""
    texts, _styles = streamlit_app._form_section_frames(_form())
    assert list(texts.columns) == [
        "Barrel%",
        "EV",
        "AtkAng",
        "IdealAtkAng%",
        "SwSp%",
        "Pull Air %",
        "Oppo Air %",
        "Hard%",
        "Pulled BRL",
    ]
    assert len(texts) == 1


def test_pulled_barrels_is_a_raw_count_with_its_bbe_sample() -> None:
    """v2.2 (D-116): the count with its window BBE, never a rate and no
    INSUFFICIENT marker (0 is a real observation); the L14 fallback names
    the window; no measurable air ball at either reach reads the absence."""
    texts, styles = streamlit_app._form_section_frames(_form())
    assert texts.at[0, "Pulled BRL"] == "2 (41 BBE)"
    assert "Pulled BRL" not in styles.columns
    texts, _ = streamlit_app._form_section_frames(
        _form(
            pulled_barrels=FormValue(value=Decimal(1), sample=63, window_days=14, sufficient=True)
        )
    )
    assert texts.at[0, "Pulled BRL"] == "1 (63 BBE) · L14"
    texts, styles = streamlit_app._form_section_frames(
        _form(pulled_barrels=FormValue(value=None, sample=0, window_days=7, sufficient=False))
    )
    assert texts.at[0, "Pulled BRL"] == "not enough data available"
    assert styles.at[0, "Pulled BRL"] == streamlit_app._REASON_CSS


def test_present_and_sufficient_cell_is_the_plain_value() -> None:
    texts, styles = streamlit_app._form_section_frames(
        _form(
            barrel_pct=FormValue(value=Decimal("18.24"), sample=22, window_days=7, sufficient=True)
        )
    )
    assert texts.at[0, "Barrel%"] == "18.2"
    # No CSS is carried for an ordinary value — the styles frame holds only
    # styled cells, and styled_text_frame reindexes it onto the wider texts.
    assert "Barrel%" not in styles.columns
    assert "L14" not in texts.at[0, "Barrel%"]


def test_l14_fallback_cell_names_the_window() -> None:
    texts, styles = streamlit_app._form_section_frames(
        _form(
            pull_air_pct=FormValue(
                value=Decimal("41.7"), sample=18, window_days=14, sufficient=True
            )
        )
    )
    assert texts.at[0, "Pull Air %"] == "41.7 · L14"
    assert "Pull Air %" not in styles.columns  # the fallback is a value, not a state


def test_below_floor_cell_keeps_value_sample_and_insufficient_marker() -> None:
    """D-068/D-023: below floor is present with its value, its exact sample,
    and the marker — never absent, and the amber CSS stays opaque."""
    texts, styles = streamlit_app._form_section_frames(
        _form(
            ideal_attack_angle_pct=FormValue(
                value=Decimal("58.0"), sample=9, window_days=14, sufficient=False
            )
        )
    )
    assert texts.at[0, "IdealAtkAng%"] == "58.0 · n=9 · INSUFFICIENT"
    assert styles.at[0, "IdealAtkAng%"] == streamlit_app._INSUFFICIENT_CSS


def test_absent_metric_reads_not_enough_data_available() -> None:
    """Nothing at either reach: D-078's wording, muted-reason styling."""
    texts, styles = streamlit_app._form_section_frames(
        _form(hard_hit_pct=FormValue(value=None, sample=0, window_days=7, sufficient=False))
    )
    assert texts.at[0, "Hard%"] == "not enough data available"
    assert styles.at[0, "Hard%"] == streamlit_app._REASON_CSS


def test_board_renders_with_selectable_grids_and_invites_selection(
    _staged_app: SlateBoard,  # noqa: F811
) -> None:
    """The selectable Sluggers grid still renders the outage board cleanly and
    names its invitation while nothing is selected; no dialog is called."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    captions = [element.value for element in at.caption]
    assert any("Select a row to open the batter's detail." in c for c in captions)
