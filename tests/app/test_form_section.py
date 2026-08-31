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
    sufficient = FormValue(value=Decimal("10"), sample=20, window_games=7, sufficient=True)
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
            FormValue(value=Decimal(2), sample=41, window_games=7, sufficient=True),
        ),
        at_bats=overrides.get(
            "at_bats", FormValue(value=Decimal(26), sample=30, window_games=7, sufficient=True)
        ),
        hits=overrides.get(
            "hits", FormValue(value=Decimal(9), sample=30, window_games=7, sufficient=True)
        ),
        pull_pct=overrides.get(
            "pull_pct", FormValue(value=Decimal("41.2"), sample=24, window_games=7, sufficient=True)
        ),
    )


def test_columns_are_the_d144_set_in_order() -> None:
    """D-144 (PO): the AB/H volume counts open the table, Pull % sits right
    before Pull Air %, the AtkAng and Pulled BRL columns are gone, and the
    Form Score closes it — D-132's actual graded subtotal."""
    texts, _styles = streamlit_app._form_section_frames(_form())
    assert list(texts.columns) == [
        "AB",
        "H",
        "Barrel%",
        "EV",
        "IdealAtkAng%",
        "Pull %",
        "Pull Air %",
        "Oppo Air %",
        "Form Score",
    ]
    assert len(texts) == 1


def test_form_score_shows_the_actual_graded_subtotal() -> None:
    """D-132 (PO): the actual form score out of the category max, never a
    placeholder dash; a card with no evaluated grade names the absence
    rather than inventing a number."""
    texts, styles = streamlit_app._form_section_frames(_form(), "1.5 / 2")
    assert texts.at[0, "Form Score"] == "1.5 / 2"
    assert "Form Score" not in styles.columns  # a present value, no reason fill
    texts, styles = streamlit_app._form_section_frames(_form())
    assert texts.at[0, "Form Score"] == "not evaluated"
    assert styles.at[0, "Form Score"] == streamlit_app._REASON_CSS


def test_the_volume_counts_open_the_table_without_bands() -> None:
    """D-144 (PO): AB and H are plain integers with the L14 fallback named
    — a count carries no sample floor, no INSUFFICIENT marker and no band
    (volume is context, not quality); no plate appearance at either reach
    names the absence."""
    texts, styles = streamlit_app._form_section_frames(
        _form(
            at_bats=FormValue(value=Decimal(26), sample=30, window_games=7, sufficient=True),
            hits=FormValue(value=Decimal(9), sample=30, window_games=7, sufficient=True),
        )
    )
    assert texts.at[0, "AB"] == "26"
    assert texts.at[0, "H"] == "9"
    assert "AB" not in styles.columns
    assert "H" not in styles.columns
    texts, styles = streamlit_app._form_section_frames(
        _form(
            at_bats=FormValue(value=Decimal(0), sample=2, window_games=14, sufficient=True),
        )
    )
    assert texts.at[0, "AB"] == "0 · L14"  # 0 is a real observation of a played window
    texts, styles = streamlit_app._form_section_frames(_form(at_bats=None, hits=None))
    assert texts.at[0, "AB"] == "not enough data available"
    assert styles.at[0, "AB"] == streamlit_app._REASON_CSS
    assert texts.at[0, "H"] == "not enough data available"


def test_present_and_sufficient_cell_is_the_plain_value_with_its_band() -> None:
    """D-129 (PO): a present, sufficient rate shows its value and wears its
    researched band — 18.2 barrels per 100 batted balls is elite."""
    texts, styles = streamlit_app._form_section_frames(
        _form(
            barrel_pct=FormValue(value=Decimal("18.24"), sample=22, window_games=7, sufficient=True)
        )
    )
    assert texts.at[0, "Barrel%"] == "18.2"
    assert styles.at[0, "Barrel%"] == streamlit_app._BAND_G3_CSS
    assert "L14" not in texts.at[0, "Barrel%"]
    # D-144 (PO): Pull % greens open at the PO's 40 line — 41.2 lands the
    # first green, 46.0 the strong one; a league-average 36.5 stays neutral.
    texts, styles = streamlit_app._form_section_frames(
        _form(pull_pct=FormValue(value=Decimal("41.2"), sample=24, window_games=7, sufficient=True))
    )
    assert texts.at[0, "Pull %"] == "41.2"
    assert styles.at[0, "Pull %"] == streamlit_app._BAND_G1_CSS
    texts, styles = streamlit_app._form_section_frames(
        _form(pull_pct=FormValue(value=Decimal("46.0"), sample=24, window_games=7, sufficient=True))
    )
    assert styles.at[0, "Pull %"] == streamlit_app._BAND_G2_CSS
    texts, styles = streamlit_app._form_section_frames(
        _form(pull_pct=FormValue(value=Decimal("36.5"), sample=24, window_games=7, sufficient=True))
    )
    assert "Pull %" not in styles.columns  # the neutral middle — no fill


def test_l14_fallback_cell_names_the_window_and_keeps_its_band() -> None:
    texts, styles = streamlit_app._form_section_frames(
        _form(
            pull_air_pct=FormValue(
                value=Decimal("41.7"), sample=18, window_games=14, sufficient=True
            )
        )
    )
    assert texts.at[0, "Pull Air %"] == "41.7 · L14"
    assert styles.at[0, "Pull Air %"] == streamlit_app._BAND_G2_CSS  # 41.7 ≥ the 38 strong edge


def test_below_floor_cell_keeps_value_sample_and_insufficient_marker() -> None:
    """D-068/D-023: below floor is present with its value, its exact sample,
    and the marker — never absent, and the amber CSS stays opaque. D-129:
    the amber outranks the band (58.0 would otherwise be a green)."""
    texts, styles = streamlit_app._form_section_frames(
        _form(
            ideal_attack_angle_pct=FormValue(
                value=Decimal("58.0"), sample=9, window_games=14, sufficient=False
            )
        )
    )
    assert texts.at[0, "IdealAtkAng%"] == "58.0 · n=9 · INSUFFICIENT"
    assert styles.at[0, "IdealAtkAng%"] == streamlit_app._INSUFFICIENT_CSS


def test_absent_metric_reads_not_enough_data_available() -> None:
    """Nothing at either reach: D-078's wording, muted-reason styling — an
    absence outranks a band (D-129)."""
    texts, styles = streamlit_app._form_section_frames(
        _form(barrel_pct=FormValue(value=None, sample=0, window_games=7, sufficient=False))
    )
    assert texts.at[0, "Barrel%"] == "not enough data available"
    assert styles.at[0, "Barrel%"] == streamlit_app._REASON_CSS


def test_form_band_edges_print_on_their_surface() -> None:
    """D-079/D-129: every edge the table uses prints on the surface — the
    hovers carry the per-metric scales, and Oppo Air %'s hover names its
    neutrality (a fit read, never a quality grade)."""
    assert "elite ≥ 13" in streamlit_app._FORM_HELP["Barrel%"]
    assert "elite ≥ 91" in streamlit_app._FORM_HELP["EV"]
    assert "elite ≥ 60" in streamlit_app._FORM_HELP["IdealAtkAng%"]
    assert "elite ≥ 48" in streamlit_app._FORM_HELP["Pull %"]
    assert "No cell colors" in streamlit_app._FORM_HELP["Oppo Air %"]
    for column in (
        "AB",
        "H",
        "Barrel%",
        "EV",
        "IdealAtkAng%",
        "Pull %",
        "Pull Air %",
        "Oppo Air %",
        "Form Score",
    ):
        assert column in streamlit_app._FORM_HELP


def test_board_renders_with_selectable_grids_and_invites_selection(
    _staged_app: SlateBoard,  # noqa: F811
) -> None:
    """The Sluggers bubble rows still render the outage board cleanly and
    name their invitation while no More button has been pressed; no dialog
    is called (D-126: buttons replaced the selectable grid)."""
    at = AppTest.from_file(str(_APP_PATH), default_timeout=_TIMEOUT)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    captions = [element.value for element in at.caption]
    assert any("More opens the batter's detail." in c for c in captions)
