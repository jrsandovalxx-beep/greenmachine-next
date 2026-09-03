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

from decimal import Decimal

from greenmachine.domain.enums import MissingReason
from greenmachine.live.grading import (
    BatterPitchLine,
    MatchupInput,
    PitchMixRow,
    derive_pitch_mix_pressure,
    derive_put_away_exploitation,
)


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
