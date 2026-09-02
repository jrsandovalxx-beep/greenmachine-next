"""GMF-001 criterion 4: the pinned Savant park-factor snapshot, bound.

The committed CSV is digest-pinned to the provenance record's certified value,
its shape is asserted, and the join to the park reference is proven total in
both directions: the published 2024-2026 three-season board (D-172, PO)
covers twenty-nine venues, and Sutter Health Park joins from its published
2025-2026 two-season board, so every Savant row matches a reference venue
and every reference venue has its Savant row.
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

PINNED_SHA256 = "0cd621959fb47adebb008ac1a09f03d55b48474cead39fd9e91d1476ce16b7c7"


def _rows() -> list[dict[str, str]]:
    with SNAPSHOT.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_the_snapshot_bytes_match_the_certified_digest() -> None:
    assert SNAPSHOT.is_file()
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == PINNED_SHA256
    assert len(SNAPSHOT.read_bytes()) == 7457


def test_the_provenance_record_sits_beside_the_snapshot_and_pins_it() -> None:
    text = PROVENANCE.read_text(encoding="utf-8")
    assert PINNED_SHA256 in text
    assert "2026-09-02" in text  # the scripted pulls' date (D-172)
    assert "baseballsavant.mlb.com" in text  # the source URL, documented not fetched
    assert "scripted pulls" in text  # the D-172 acquisition, stated honestly
    assert "published" in text  # every number straight off a board Savant publishes


def test_snapshot_shape_60_rows_30_venues_two_sides() -> None:
    rows = _rows()
    assert len(rows) == 60
    assert len(rows[0]) == 27
    by_venue: dict[str, list[str]] = {}
    for row in rows:
        by_venue.setdefault(row["venue_id"], []).append(row["key_bat_side"])
    assert len(by_venue) == 30
    assert all(sorted(sides) == ["L", "R"] for sides in by_venue.values())


def test_the_windows_are_the_two_published_boards_d172_documents() -> None:
    """D-172 (PO): Savant's published 2024-2026 three-year board for the
    twenty-nine venues it covers; Sutter Health Park (opened 2025) reads
    Savant's published 2025-2026 two-year board. The meta fields are
    Savant's own page flags, copied verbatim — nothing is derived."""
    for row in _rows():
        assert row["key_year"] == "2026"  # both windows' end season
        if row["venue_id"] == "2529":  # Sutter Health Park's two rows
            assert row["key_num_years_rolling"] == "2"
            assert row["year_range"] == "2025-2026"
        else:
            assert row["key_num_years_rolling"] == "3"
            assert row["key_is_year_rolling"] == "1"
            assert row["year_range"] == "2024-2026"


def test_every_savant_row_joins_a_reference_venue() -> None:
    """Total in both directions since D-166 closed the Athletics' gap, held
    through the D-172 window change: the two published boards list the same
    thirty current venues between them."""
    reference_ids = {v.savant_venue_id for v in PARK_VENUES if v.savant_venue_id is not None}
    snapshot_ids = {int(row["venue_id"]) for row in _rows()}
    unmatched = snapshot_ids - reference_ids
    assert unmatched == set(), f"Savant rows with no reference venue: {sorted(unmatched)}"
    assert snapshot_ids == reference_ids  # 30 == 30, and the same 30


def test_n_pa_is_positive_everywhere_and_spans_the_stated_range() -> None:
    values = sorted(int(row["n_pa"]) for row in _rows())
    assert values[0] == 13865  # Sutter Health Park, LHB — its two played seasons
    assert values[-1] == 32992  # Daikin Park, RHB
    assert all(value > 0 for value in values)


def test_the_athletics_gap_is_closed_with_real_numbers() -> None:
    """D-172 (PO): Sutter Health Park's factors come straight off Savant's
    published two-season board — 120 (LHB) / 122 (RHB) — joined on Savant
    venue id 2529, never filled in from a league average."""
    athletics = next(v for v in PARK_VENUES if v.team == "Athletics")
    assert athletics.savant_venue_id == 2529
    rows = [row for row in _rows() if row["venue_id"] == "2529"]
    assert {row["key_bat_side"]: row["index_hr"] for row in rows} == {"L": "120", "R": "122"}


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
    factor = ParkFactor(factor=Decimal("120"), handedness=Handedness.LEFT, plate_appearances=13865)
    assert factor.plate_appearances == 13865  # D-014: beside, never fused
    with pytest.raises(InputContractError):
        ParkFactor(factor=Decimal("120"), handedness=Handedness.LEFT, plate_appearances=0)
