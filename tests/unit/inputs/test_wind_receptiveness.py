"""D-122: the Ballpark Pal wind-receptiveness snapshot's guarantees.

The values were transcribed from the committed PO printout capture; what
the suite pins is what a local test can honestly pin: the digest gate
authenticates the committed bytes before a row is read, the table covers
exactly the thirty reference venues, and the direction-specific values
stay Decimals in the model's plausible band — so a transcription slip or
a drifted file fails here rather than mis-colouring a wind cell on the
Conditions tab.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from greenmachine.inputs import PARK_VENUES, read_receptiveness
from greenmachine.inputs.errors import InputContractError
from greenmachine.inputs.wind_receptiveness import (
    EXPECTED_ROWS,
    PINNED_BYTES,
    PINNED_SHA256,
    snapshot_path,
)


def test_the_snapshot_satisfies_its_own_provenance() -> None:
    raw = snapshot_path().read_bytes()
    import hashlib

    assert hashlib.sha256(raw).hexdigest() == PINNED_SHA256
    assert len(raw) == PINNED_BYTES


def test_the_table_covers_exactly_the_thirty_venues() -> None:
    receptiveness = read_receptiveness()
    assert len(receptiveness) == EXPECTED_ROWS == 30
    assert set(receptiveness) == {venue.venue_id for venue in PARK_VENUES}


def test_every_value_is_a_decimal_in_the_models_band() -> None:
    for venue_id, recept in read_receptiveness().items():
        for value in (recept.recept_in, recept.recept_out, recept.recept_overall):
            assert isinstance(value, Decimal), venue_id
            assert Decimal("-10") < value < Decimal("10"), venue_id


def test_direction_specific_signs_survive_the_transcription() -> None:
    """The printout's two direction-split oddities — Angel Stadium's
    suppressing out-wind and Daikin Park's suppressing in-wind — are the
    rows a hand transcription is most likely to 'fix'."""
    receptiveness = read_receptiveness()
    assert receptiveness["angel-stadium"].recept_out == Decimal("-2.36")
    assert receptiveness["angel-stadium"].recept_in == Decimal("3.32")
    assert receptiveness["daikin-park"].recept_in == Decimal("-3.21")
    assert receptiveness["wrigley-field"].recept_overall == Decimal("9.15")
    assert receptiveness["rogers-centre"].recept_overall == Decimal("-2.39")


def test_a_drifted_snapshot_is_refused(tmp_path) -> None:
    moved = tmp_path / "moved.csv"
    moved.write_text("venue_id,recept_in,recept_out,recept_overall\n", encoding="utf-8")
    with pytest.raises(InputContractError, match="digest mismatch"):
        read_receptiveness(moved)
    with pytest.raises(InputContractError, match="not found"):
        read_receptiveness(tmp_path / "absent.csv")
