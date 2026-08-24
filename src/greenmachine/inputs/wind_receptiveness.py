"""The pinned Ballpark Pal wind-receptiveness snapshot (D-082, entered as data by D-122).

The Product Owner's printout of Ballpark Pal's park factors — model years
2023-2025, adjusted for yearly ball changes, captured 2026-08-21 — lives at
``docs/reference/ballpark-pal-park-factors.md`` and was parked until the
wind work shipped: D-082's stadium panel and the Conditions-tab wind colour
rule both consume it, and the capture's own header made the terms —
reference material only until a DECISIONS.md entry and a SourceRecord
carry it. D-122 is that entry and this module is that record. The same
three properties as the Savant factor snapshot hold by construction:

- **The digest is verified before a row is parsed.** If the committed
  bytes moved, nothing is returned at all.
- **No fetch, ever.** The only input is a committed file path; the source
  URL lives in the provenance record as documentation of the Product
  Owner's capture, never as an address this code could dial (D-057
  boundary 1).
- **Display only.** Receptiveness colours a Conditions cell; it is not a
  grading component, a tag input, or a park factor, and nothing here
  feeds the model.

The values are the model's HR-effect sensitivity to wind per direction:
``recept_out`` applies when the wind blows out, ``recept_in`` when it
blows in, and ``recept_overall`` is the all-wind summary the surface
quotes. Positive raises the home-run effect, negative suppresses it,
near-zero means the venue barely notices. The sign can differ by
direction at the same venue — Angel Stadium's out-wind reads suppressing
while its in-wind reads helping — which is why the colour rule reads the
direction-specific value rather than the overall sign. All thirty venues
carry a row: Tropicana Field's receptiveness is published even though its
speed and frequency cells were blank on the printout, and a roofed
venue's row simply never meets a wind reading to colour.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from greenmachine.inputs.contract import (
    ManualExportProvenance,
    SourceKind,
    SourceRecord,
)
from greenmachine.inputs.errors import InputContractError
from greenmachine.inputs.park_reference import PARK_VENUES

SOURCE_ID = "ballpark-pal-wind-receptiveness"

PINNED_SHA256 = "6f823572bc6bef57241ac94df253d5afb07623dc38ba5a2b1a698c66d86c7467"
PINNED_BYTES = 947
EXPECTED_ROWS = 30

PROVENANCE = ManualExportProvenance(
    source_url="https://www.ballparkpal.com/Park-Factors-General.php",
    export_date=date(2026, 8, 21),
    row_count=EXPECTED_ROWS,
    sha256=PINNED_SHA256,
)

SOURCE = SourceRecord(
    source_id=SOURCE_ID,
    kind=SourceKind.MANUAL_EXPORT,
    description=(
        "Ballpark Pal per-park wind receptiveness (modelled HR-effect "
        "sensitivity to wind, In/Out/Overall), model years 2023-2025, "
        "adjusted for yearly ball changes - transcribed from the Product "
        "Owner's printout capture of 2026-08-21 (the wind work D-082 set "
        "aside), entered as data by D-122; display colour only, never "
        "grading"
    ),
    provenance=PROVENANCE,
)


@dataclass(frozen=True)
class WindReceptiveness:
    """One park's modelled HR-effect sensitivity to wind, per direction."""

    recept_in: Decimal
    recept_out: Decimal
    recept_overall: Decimal


def snapshot_path() -> Path:
    """The committed snapshot's path — the only input this module has."""
    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "ballpark_pal_wind_receptiveness_2023-2025.csv"  # the D-122 pin (§GMF-001 c4)
    )


def _verified_text(path: Path) -> str:
    """The file's text, or nothing at all: the digest gate.

    Reads bytes, authenticates them, and only then decodes. A caller cannot
    obtain unverified rows from this module because there is no other door.
    """
    if not path.is_file():
        raise InputContractError(f"pinned wind-receptiveness snapshot not found at {path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PINNED_SHA256:
        raise InputContractError(
            f"pinned wind-receptiveness snapshot digest mismatch: expected {PINNED_SHA256}, "
            f"computed {digest} — the committed export moved, and no row is read "
            "from bytes the provenance record does not certify"
        )
    if len(raw) != PINNED_BYTES:
        raise InputContractError(
            f"pinned wind-receptiveness snapshot is {len(raw)} bytes, expected {PINNED_BYTES}"
        )
    return raw.decode("utf-8")


def read_receptiveness(path: Path | None = None) -> dict[str, WindReceptiveness]:
    """Every pinned row as ``WindReceptiveness`` values, keyed by venue id.

    The shape the provenance record declares is enforced here, not assumed:
    exactly thirty rows and exactly the thirty reference venues — a snapshot
    that half-matched would otherwise colour some parks and silently skip
    others.
    """
    text = _verified_text(path if path is not None else snapshot_path())
    rows = list(csv.DictReader(text.splitlines()))
    if len(rows) != EXPECTED_ROWS:
        raise InputContractError(f"pinned snapshot has {len(rows)} rows, expected {EXPECTED_ROWS}")

    receptiveness: dict[str, WindReceptiveness] = {}
    for row in rows:
        venue_id = row["venue_id"]
        if venue_id in receptiveness:
            raise InputContractError(f"pinned snapshot repeats venue {venue_id!r}")
        receptiveness[venue_id] = WindReceptiveness(
            recept_in=Decimal(row["recept_in"]),
            recept_out=Decimal(row["recept_out"]),
            recept_overall=Decimal(row["recept_overall"]),
        )
    known = {venue.venue_id for venue in PARK_VENUES}
    if set(receptiveness) != known:
        raise InputContractError(
            f"pinned snapshot venues disagree with the reference table: "
            f"unexpected {sorted(set(receptiveness) - known)}, "
            f"missing {sorted(known - set(receptiveness))}"
        )
    return receptiveness
