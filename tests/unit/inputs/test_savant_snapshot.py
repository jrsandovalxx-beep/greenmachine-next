"""GMF-001 criterion 4: the pinned Savant park-factor snapshot, bound.

The committed CSV is digest-pinned to the provenance record's certified value,
its shape is asserted, and the join to the park reference is proven total in
both directions since D-166: the two-season window covers Sutter Health Park,
so every Savant row matches a reference venue and every reference venue has
its Savant row.
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
SNAPSHOT = REPO_ROOT / "data" / "savant_park_factors_2025-2026.csv"
PROVENANCE = REPO_ROOT / "data" / "SAVANT_PARK_FACTORS_PROVENANCE.md"

PINNED_SHA256 = "c077ec837e811a470b47c614eaa1bc173fa5d22d5de241d256dd869cce920d73"


def _rows() -> list[dict[str, str]]:
    with SNAPSHOT.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_the_snapshot_bytes_match_the_certified_digest() -> None:
    assert SNAPSHOT.is_file()
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == PINNED_SHA256
    assert len(SNAPSHOT.read_bytes()) == 7505


def test_the_provenance_record_sits_beside_the_snapshot_and_pins_it() -> None:
    text = PROVENANCE.read_text(encoding="utf-8")
    assert PINNED_SHA256 in text
    assert "2026-09-01" in text  # the scripted pull date (D-166)
    assert "baseballsavant.mlb.com" in text  # the source URL, documented not fetched
    assert "scripted pull" in text  # the D-166 acquisition, stated honestly


def test_snapshot_shape_60_rows_30_venues_two_sides() -> None:
    rows = _rows()
    assert len(rows) == 60
    assert len(rows[0]) == 27
    by_venue: dict[str, list[str]] = {}
    for row in rows:
        by_venue.setdefault(row["venue_id"], []).append(row["key_bat_side"])
    assert len(by_venue) == 30
    assert all(sorted(sides) == ["L", "R"] for sides in by_venue.values())


def test_the_window_is_uniform_and_two_season_rolling() -> None:
    """D-166 (PO): the only uniform window that can cover Sutter Health Park
    (opened 2025) is one that does not reach back to 2024."""
    for row in _rows():
        assert row["key_year"] == "2026"
        assert row["key_num_years_rolling"] == "2"
        assert row["key_is_year_rolling"] == "-1"  # Savant's true flag on this board
        assert row["year_range"] == "2025-2026"


def test_every_savant_row_joins_a_reference_venue() -> None:
    """Total in both directions since D-166 closed the Athletics' gap."""
    reference_ids = {v.savant_venue_id for v in PARK_VENUES if v.savant_venue_id is not None}
    snapshot_ids = {int(row["venue_id"]) for row in _rows()}
    unmatched = snapshot_ids - reference_ids
    assert unmatched == set(), f"Savant rows with no reference venue: {sorted(unmatched)}"
    assert snapshot_ids == reference_ids  # 30 == 30, and the same 30


def test_n_pa_is_positive_everywhere_and_spans_the_stated_range() -> None:
    values = sorted(int(row["n_pa"]) for row in _rows())
    assert values[0] == 6995  # Tropicana Field, LHB — the provenance floor
    assert values[-1] == 21365  # Daikin Park, RHB
    assert all(value > 0 for value in values)


def test_the_athletics_gap_is_closed_with_real_numbers() -> None:
    """D-166 (PO): Sutter Health Park's factors are the source's own numbers —
    119 (LHB) / 122 (RHB) — joined on Savant venue id 2529, never filled in
    from a league average."""
    athletics = next(v for v in PARK_VENUES if v.team == "Athletics")
    assert athletics.savant_venue_id == 2529
    rows = [row for row in _rows() if row["venue_id"] == "2529"]
    assert {row["key_bat_side"]: row["index_hr"] for row in rows} == {"L": "119", "R": "122"}


def test_not_yet_observed_is_a_state_not_a_number() -> None:
    """The absence machinery stands for any venue a future snapshot does not
    cover: NOT_YET_OBSERVED — the source answered completely, and
    SOURCE_UNAVAILABLE would assert a failure that did not happen."""
    field: SnapshotField[ParkFactor] = SnapshotField.absent(
        AbsenceReason.NOT_YET_OBSERVED, "savant-park-factors"
    )
    assert field.display_state() is DisplayState.NOT_YET_OBSERVED
    assert field.value is None  # cannot be read as a number


def test_a_park_factor_carries_its_sample_beside_the_value() -> None:
    factor = ParkFactor(factor=Decimal("119"), handedness=Handedness.LEFT, plate_appearances=13794)
    assert factor.plate_appearances == 13794  # D-014: beside, never fused
    with pytest.raises(InputContractError):
        ParkFactor(factor=Decimal("119"), handedness=Handedness.LEFT, plate_appearances=0)
