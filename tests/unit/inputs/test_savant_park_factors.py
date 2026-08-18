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
    moved = tmp_path / "savant_park_factors_2024-2026.csv"
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
    # The provenance record's independently witnessed value (its verification
    # table): Fenway LHB index_hr = 82 over 23,125 PA.
    assert lhb.factor == Decimal("82")
    assert lhb.plate_appearances == 23125


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


def test_the_athletics_gap_is_represented_never_filled() -> None:
    """Provenance finding 1 as behaviour: no row, no number, and the reason is
    NOT_YET_OBSERVED — the export answered completely."""
    factors = read_factors()
    athletics = next(v for v in PARK_VENUES if v.savant_venue_id is None)
    fields = factor_fields(athletics, factors)
    for field in fields.values():
        assert field.value is None
        assert field.absence is AbsenceReason.NOT_YET_OBSERVED
        assert field.display_state() is DisplayState.NOT_YET_OBSERVED
        assert field.source_id == SOURCE_ID  # a source-dependent absence names it


def test_the_source_record_carries_the_manual_export_provenance() -> None:
    assert SOURCE.provenance is PROVENANCE
    assert PROVENANCE.sha256 == PINNED_SHA256
    assert PROVENANCE.export_date.isoformat() == "2026-08-06"
    assert PROVENANCE.row_count == EXPECTED_ROWS


def test_the_basis_statement_says_rolling_window_and_export_date() -> None:
    """The provenance record requires any screen rendering these values to say
    it is a three-season rolling window; this is that promise, kept in words."""
    statement = basis_statement()
    assert window_label() in statement
    assert "rolling" in statement
    assert "2026-08-06" in statement
    assert "100 = neutral" in statement
    assert "never fetched" in statement


def test_no_url_is_dialable_from_the_reader() -> None:
    """D-057 boundary 1 at the module level: the source URL exists only inside
    the provenance record, and no HTTP machinery accompanies it."""
    source = Path(read_factors.__module__.replace(".", "/") + ".py")
    text = (Path(__file__).resolve().parents[3] / "src" / source).read_text(encoding="utf-8")
    for banned in ("requests", "urllib", "httpx", "aiohttp", "socket"):
        assert banned not in text, f"{banned!r} appears in the pinned-snapshot reader"
