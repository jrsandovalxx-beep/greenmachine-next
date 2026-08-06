"""GMF-001 criterion 4: the pinned Savant park-factor snapshot, bound.

The committed CSV is digest-pinned to the provenance record's certified value,
its shape is asserted, and the join to the park reference is proven total in
the direction that matters: every Savant row matches a reference venue. The
reverse is deliberately not total — the Athletics have no Savant row
(provenance finding 1), and that gap is represented, never filled.
"""

from __future__ import annotations

import csv
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from greenmachine.inputs import (
    PARK_VENUES,
    AbsenceReason,
    DisplayState,
    Handedness,
    InputContractError,
    ParkFactor,
    SnapshotField,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = REPO_ROOT / "data" / "savant_park_factors_2024-2026.csv"
PROVENANCE = REPO_ROOT / "data" / "SAVANT_PARK_FACTORS_PROVENANCE.md"

PINNED_SHA256 = "2bbaee9d049008bdd9887f8c68feecc683c4e1803513b12c9797cb9037252ebf"


def _rows() -> list[dict[str, str]]:
    with SNAPSHOT.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_the_snapshot_bytes_match_the_certified_digest() -> None:
    assert SNAPSHOT.is_file()
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == PINNED_SHA256
    assert len(SNAPSHOT.read_bytes()) == 7196


def test_the_provenance_record_sits_beside_the_snapshot_and_pins_it() -> None:
    text = PROVENANCE.read_text(encoding="utf-8")
    assert PINNED_SHA256 in text
    assert "2026-08-06" in text  # the manual export date
    assert "baseballsavant.mlb.com" in text  # the source URL, documented not fetched
    assert "Save Page As" in text  # the manual method (D-057 boundary 1)


def test_snapshot_shape_58_rows_29_venues_two_sides() -> None:
    rows = _rows()
    assert len(rows) == 58
    assert len(rows[0]) == 27
    by_venue: dict[str, list[str]] = {}
    for row in rows:
        by_venue.setdefault(row["venue_id"], []).append(row["key_bat_side"])
    assert len(by_venue) == 29
    assert all(sorted(sides) == ["L", "R"] for sides in by_venue.values())


def test_the_window_is_uniform_and_three_season_rolling() -> None:
    for row in _rows():
        assert row["key_year"] == "2026"
        assert row["key_num_years_rolling"] == "3"
        assert row["key_is_year_rolling"] == "1"
        assert row["year_range"] == "2024-2026"


def test_every_savant_row_joins_a_reference_venue() -> None:
    """Total in the direction that matters (the reverse is finding 1)."""
    reference_ids = {v.savant_venue_id for v in PARK_VENUES if v.savant_venue_id is not None}
    snapshot_ids = {int(row["venue_id"]) for row in _rows()}
    unmatched = snapshot_ids - reference_ids
    assert unmatched == set(), f"Savant rows with no reference venue: {sorted(unmatched)}"
    assert snapshot_ids == reference_ids  # 29 == 29, and the same 29


def test_n_pa_is_positive_everywhere_and_spans_the_stated_range() -> None:
    values = sorted(int(row["n_pa"]) for row in _rows())
    assert values[0] == 13560  # Tropicana Field, LHB — the provenance floor
    assert values[-1] == 31517
    assert all(value > 0 for value in values)


def test_a_club_without_a_savant_row_renders_the_absent_state_never_a_number() -> None:
    """Provenance finding 1 as a property: the gap is represented, not filled."""
    athletics = next(v for v in PARK_VENUES if v.savant_venue_id is None)
    assert athletics.team == "Athletics"
    field: SnapshotField[ParkFactor] = SnapshotField.absent(
        AbsenceReason.SOURCE_UNAVAILABLE, "savant-park-factors"
    )
    assert field.display_state() is DisplayState.SOURCE_UNAVAILABLE
    assert field.value is None  # cannot be read as a number


def test_a_park_factor_carries_its_sample_beside_the_value() -> None:
    factor = ParkFactor(factor=Decimal("82"), handedness=Handedness.LEFT, plate_appearances=13560)
    assert factor.plate_appearances == 13560  # D-014: beside, never fused
    with pytest.raises(InputContractError):
        ParkFactor(factor=Decimal("82"), handedness=Handedness.LEFT, plate_appearances=0)
