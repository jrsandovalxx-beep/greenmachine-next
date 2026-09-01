"""The pinned Savant park-factor snapshot, read as contract values (§GMF-004 c2).

GMF-001 committed the snapshot and its provenance record; this module is the
first code that reads it. Three properties hold by construction:

- **The digest is verified before a row is parsed.** Not after, and not
  alongside: a reader that parses first and checks later has already acted on
  bytes it had not authenticated. If the bytes moved, nothing is returned at
  all.
- **No fetch at runtime, ever.** The only input is a committed file path.
  There is no URL here and no HTTP client anywhere in the tree (D-057
  boundary 1); the source URL lives in the provenance record as documentation
  of how the snapshot was taken, and nowhere as an address this code could
  dial. D-166 (PO: no preference between the two) moved the acquisition
  itself from the D-057 hand export to a scripted pull of the leaderboard's
  embedded data payload — the same Savant host the live app reads daily.
- **Gaps are represented, never filled.** All thirty venues have rows: the
  snapshot is the 2023-2026 four-season window (D-171, PO), which covers
  Sutter Health Park (opened 2025) on its two played seasons. Savant
  publishes no four-year window — only one, two or three rolling years — so
  each venue-side factor is the plate-appearance-weighted blend of its
  single-year boards, pulled once and derived by the deterministic rule the
  provenance record documents. A venue a future snapshot does not cover
  still comes back absent with ``NOT_YET_OBSERVED``: ``SOURCE_UNAVAILABLE``
  would assert a failure that did not happen, and a league-average
  substitute would invent one.

``index_hr`` is the column this product consumes — the home-run park factor —
not ``index_woba``, the leaderboard's headline number. The two sit adjacent in
the same row and mean different things, so the choice is named here and
asserted by test rather than left to a column-order accident.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path

from greenmachine.inputs.contract import (
    AbsenceReason,
    Handedness,
    ManualExportProvenance,
    ParkFactor,
    ParkVenue,
    SnapshotField,
    SourceKind,
    SourceRecord,
)
from greenmachine.inputs.errors import InputContractError

SOURCE_ID = "savant-park-factors"

PINNED_SHA256 = "67ca75125fdeaab6db854267f85161969e855a6932983bb7f83f68033eecf5f4"
PINNED_BYTES = 7506
EXPECTED_ROWS = 60
EXPECTED_VENUES = 30

FACTOR_COLUMN = "index_hr"
SAMPLE_COLUMN = "n_pa"

_SIDES = {"L": Handedness.LEFT, "R": Handedness.RIGHT}

PROVENANCE = ManualExportProvenance(
    source_url=(
        # The D-171 acquisition is eight scripted pulls — the four single-year
        # boards per bat side — blended by the rule the provenance record
        # documents; the leaderboard page stands here as the documented origin.
        "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors"
    ),
    export_date=date(2026, 9, 1),
    row_count=EXPECTED_ROWS,
    sha256=PINNED_SHA256,
)

SOURCE = SourceRecord(
    source_id=SOURCE_ID,
    kind=SourceKind.MANUAL_EXPORT,
    description=(
        "Savant per-handedness park factors, index_hr, "
        "2023-2026 four-season window - derived from the four single-year "
        "boards, plate-appearance-weighted per venue-side (D-171, PO: "
        "Savant publishes no four-year window), pulled once, pinned and "
        "never fetched at runtime"
    ),
    provenance=PROVENANCE,
)


def snapshot_path() -> Path:
    """The committed snapshot's path — the only input this module has."""
    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "savant_park_factors_2023-2026.csv"  # the §GMF-001 criterion 4 pin
    )


def _verified_text(path: Path) -> str:
    """The file's text, or nothing at all: the digest gate.

    Reads bytes, authenticates them, and only then decodes. A caller cannot
    obtain unverified rows from this module because there is no other door.
    """
    if not path.is_file():
        raise InputContractError(f"pinned Savant snapshot not found at {path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PINNED_SHA256:
        raise InputContractError(
            f"pinned Savant snapshot digest mismatch: expected {PINNED_SHA256}, "
            f"computed {digest} — the committed export moved, and no row is read "
            "from bytes the provenance record does not certify"
        )
    if len(raw) != PINNED_BYTES:
        raise InputContractError(
            f"pinned Savant snapshot is {len(raw)} bytes, expected {PINNED_BYTES}"
        )
    return raw.decode("utf-8")


def read_factors(path: Path | None = None) -> dict[int, dict[Handedness, ParkFactor]]:
    """Every pinned row as ``ParkFactor`` values, keyed by Savant venue id.

    The shape the provenance record declares is enforced here, not assumed:
    60 rows, 30 venues, both bat sides for every venue, and one uniform
    window across the file. A snapshot that half-matched would otherwise
    render as a screen half-full of plausible numbers.
    """
    text = _verified_text(path if path is not None else snapshot_path())
    rows = list(csv.DictReader(text.splitlines()))
    if len(rows) != EXPECTED_ROWS:
        raise InputContractError(f"pinned snapshot has {len(rows)} rows, expected {EXPECTED_ROWS}")

    windows = {row["year_range"] for row in rows}
    if windows != {window_label()}:
        raise InputContractError(
            f"pinned snapshot mixes windows {sorted(windows)}; a single rolling "
            "window is what makes one factor comparable to the next"
        )

    factors: dict[int, dict[Handedness, ParkFactor]] = {}
    for row in rows:
        side = _SIDES.get(row["key_bat_side"])
        if side is None:
            raise InputContractError(f"unknown bat side {row['key_bat_side']!r} in pinned snapshot")
        venue_id = int(row["venue_id"])
        per_side = factors.setdefault(venue_id, {})
        if side in per_side:
            raise InputContractError(
                f"pinned snapshot repeats venue {venue_id} for bat side {row['key_bat_side']}"
            )
        per_side[side] = ParkFactor(
            factor=Decimal(row[FACTOR_COLUMN]),
            handedness=side,
            plate_appearances=int(row[SAMPLE_COLUMN]),
        )

    if len(factors) != EXPECTED_VENUES:
        raise InputContractError(
            f"pinned snapshot covers {len(factors)} venues, expected {EXPECTED_VENUES}"
        )
    incomplete = sorted(venue for venue, sides in factors.items() if len(sides) != len(_SIDES))
    if incomplete:
        raise InputContractError(
            f"pinned snapshot venues missing a bat side: {incomplete} — a venue with "
            "one side would render a blank beside a number and mean neither"
        )
    return factors


def window_label() -> str:
    """The window these factors describe, as the snapshot itself labels it."""
    return "2023-2026"


def basis_statement() -> str:
    """What the numbers are, in the user's words — stated on the screen.

    Every clause is a fact a reader needs to not misread the column: which
    metric, which window, how old, and that 100 is neutral. The provenance
    record insists any screen rendering these values says which rolling
    window they describe, and this is where that promise is kept.
    """
    return (
        f"Savant home-run park factors ({FACTOR_COLUMN}), {window_label()} four-season "
        f"window, 100 = neutral. Derived from Baseball Savant's single-year boards "
        f"pulled on {PROVENANCE.export_date.isoformat()} — Savant publishes no "
        "four-year window — pinned in the repository and never fetched at runtime."
    )


def factor_fields(
    venue: ParkVenue, factors: dict[int, dict[Handedness, ParkFactor]]
) -> dict[Handedness, SnapshotField[ParkFactor]]:
    """One venue's two factor fields — present from the snapshot, or absent.

    A venue the snapshot does not cover carries ``NOT_YET_OBSERVED`` naming
    this source: the source answered completely, and this venue is not in
    the window it published. The absence is the value (§7); nothing is
    substituted for it.
    """
    if venue.savant_venue_id is None or venue.savant_venue_id not in factors:
        return {
            side: SnapshotField[ParkFactor].absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID)
            for side in _SIDES.values()
        }
    per_side = factors[venue.savant_venue_id]
    return {side: SnapshotField.present(per_side[side], SOURCE_ID) for side in _SIDES.values()}
