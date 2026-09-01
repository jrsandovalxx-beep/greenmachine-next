"""GMF-004 criterion 2: the pinned snapshot read as contract values.

The digest gate is the property worth testing hardest — not that a good file
parses, but that a moved file yields **nothing**. A reader that validated
after parsing would already have acted on unauthenticated bytes, so the test
below corrupts the file and asserts no rows come back at all.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from greenmachine.inputs import (
    PARK_VENUES,
    AbsenceReason,
    DisplayState,
    Handedness,
    InputContractError,
    ParkVenue,
    VenueType,
)
from greenmachine.inputs.savant_park_factors import (
    EXPECTED_ROWS,
    EXPECTED_VENUES,
    FACTOR_COLUMN,
    PINNED_SHA256,
    PROVENANCE,
    SOURCE,
    SOURCE_ID,
    basis_statement,
    factor_fields,
    read_factors,
    snapshot_path,
    window_label,
)


def test_the_reader_reads_the_committed_snapshot() -> None:
    factors = read_factors()
    assert len(factors) == EXPECTED_VENUES
    assert sum(len(sides) for sides in factors.values()) == EXPECTED_ROWS
    assert all(set(sides) == {Handedness.LEFT, Handedness.RIGHT} for sides in factors.values())


def test_a_moved_file_yields_nothing_at_all(tmp_path: Path) -> None:
    """The digest gate: authenticate first, parse second.

    The corrupted copy is still perfectly valid CSV — the failure must come
    from the digest, not from a parse error, or the gate is not what stopped it.
    """
    original = snapshot_path().read_text(encoding="utf-8")
    moved = tmp_path / "savant_park_factors_2023-2026.csv"
    moved.write_text(original.replace("Angel Stadium", "Angel Stadium (edited)"), encoding="utf-8")
    with pytest.raises(InputContractError, match="digest mismatch"):
        read_factors(moved)


def test_a_missing_file_is_named_not_swallowed(tmp_path: Path) -> None:
    with pytest.raises(InputContractError, match="not found"):
        read_factors(tmp_path / "absent.csv")


def test_the_product_consumes_the_home_run_factor_not_the_headline() -> None:
    """``index_hr`` and ``index_woba`` are adjacent columns meaning different
    things; the choice is named in code and pinned here so a column-order
    change cannot quietly swap them."""
    assert FACTOR_COLUMN == "index_hr"
    factors = read_factors()
    fenway = next(v for v in PARK_VENUES if v.venue_id == "fenway-park")
    assert fenway.savant_venue_id is not None
    lhb = factors[fenway.savant_venue_id][Handedness.LEFT]
    # D-171's derived snapshot: Fenway LHB index_hr = 88 over 31,422 PA on
    # the 2023-2026 four-season window.
    assert lhb.factor == Decimal("88")
    assert lhb.plate_appearances == 31422


def test_every_venue_with_a_row_yields_two_present_fields() -> None:
    factors = read_factors()
    covered = [v for v in PARK_VENUES if v.savant_venue_id is not None]
    assert len(covered) == EXPECTED_VENUES
    for venue in covered:
        fields = factor_fields(venue, factors)
        for side, field in fields.items():
            assert field.display_state() is DisplayState.VALUE
            assert field.value is not None
            assert field.value.handedness is side  # the slot's own hand
            assert field.source_id == SOURCE_ID
            assert field.derivation is None  # sourced, never computed


def test_the_athletics_are_covered_since_d166s_gap_closure() -> None:
    """D-166 closed the Sutter Health Park gap; D-171 (PO) holds it on the
    2023-2026 window — Sutter's factor is the documented blend of its two
    played seasons, and the Athletics read real factors like every club."""
    factors = read_factors()
    athletics = next(v for v in PARK_VENUES if v.team == "Athletics")
    assert athletics.savant_venue_id == 2529
    fields = factor_fields(athletics, factors)
    assert fields[Handedness.LEFT].value is not None
    assert fields[Handedness.LEFT].value.factor == Decimal("119")
    assert fields[Handedness.LEFT].value.plate_appearances == 13438
    assert fields[Handedness.RIGHT].value is not None
    assert fields[Handedness.RIGHT].value.factor == Decimal("118")
    for field in fields.values():
        assert field.display_state() is DisplayState.VALUE
        assert field.source_id == SOURCE_ID


def test_a_venue_without_a_row_is_not_yet_observed_never_a_number() -> None:
    """The absence path stands for any venue a future snapshot does not
    cover: NOT_YET_OBSERVED — the source answered completely."""
    factors = read_factors()
    ghost = ParkVenue(
        "ghost-park",
        "Ghost Park",
        "Ghost Club",
        VenueType.OPEN_AIR,
        savant_venue_id=999999,
        latitude=Decimal("40.0"),
        longitude=Decimal("-74.0"),
    )
    fields = factor_fields(ghost, factors)
    for field in fields.values():
        assert field.value is None
        assert field.absence is AbsenceReason.NOT_YET_OBSERVED
        assert field.display_state() is DisplayState.NOT_YET_OBSERVED
        assert field.source_id == SOURCE_ID  # a source-dependent absence names it


def test_the_source_record_carries_the_pinned_provenance() -> None:
    assert SOURCE.provenance is PROVENANCE
    assert PROVENANCE.sha256 == PINNED_SHA256
    assert PROVENANCE.export_date.isoformat() == "2026-09-01"  # the D-171 scripted pulls
    assert PROVENANCE.row_count == EXPECTED_ROWS


def test_the_basis_statement_says_rolling_window_and_export_date() -> None:
    """The provenance record requires any screen rendering these values to say
    which rolling window they describe; this is that promise, kept in words."""
    statement = basis_statement()
    assert window_label() in statement
    assert "four-season" in statement
    assert "single-year boards" in statement  # the derivation is named on screen
    assert "2026-09-01" in statement
    assert "100 = neutral" in statement
    assert "never fetched" in statement


def test_no_url_is_dialable_from_the_reader() -> None:
    """D-057 boundary 1 at the module level: the source URL exists only inside
    the provenance record, and no HTTP machinery accompanies it."""
    source = Path(read_factors.__module__.replace(".", "/") + ".py")
    text = (Path(__file__).resolve().parents[3] / "src" / source).read_text(encoding="utf-8")
    for banned in ("requests", "urllib", "httpx", "aiohttp", "socket"):
        assert banned not in text, f"{banned!r} appears in the pinned-snapshot reader"
