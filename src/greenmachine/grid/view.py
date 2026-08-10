"""Display frames and hand-rolled ``Styler`` grading for the grid (GMF-002).

The contract enforces the semantics; this module's obligation is to keep them
visible at render:

- **Absence is never a blank.** Each absence state renders as its own fixed
  text — ``not applicable`` / ``not yet observed`` / ``source unavailable`` —
  visibly distinct from numeric zero and from each other. A numeric zero
  renders as a number with its sample beside it (D-014), never as an empty
  cell.
- **Grading is hand-rolled via ``Styler.map`` (D-059)** — a per-column lookup
  from rendered cell text to an inline CSS string. Present values get a
  green-is-good scale normalised within their column; each absence state gets
  its own muted, non-green style. No matplotlib anywhere.
- **The initial row order is neutral and deliberate**: batter name ascending —
  an identity order, not a metric. Every metric ordering is user-initiated in
  the component itself (*sort, don't blend*, D-015/D-017).
- **Density at the 1.37 floor**: ``st.dataframe`` exposes no row-height
  control at the version floor (D-062), so density is implemented as a
  rows-in-view viewport preset — the closest control the floor offers, named
  for what it is.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd

from greenmachine.inputs import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    BatterInputs,
    ExitVelocityAverage,
    InputSnapshot,
    SnapshotField,
    SwingShare,
    Window,
    WindowedBatterMetrics,
)

if TYPE_CHECKING:
    from pandas.io.formats.style import Styler

BATTER_COLUMN = "Batter"

# Canonical metric order — the D-023 power surface, as the contract names it.
METRIC_COLUMNS: tuple[str, ...] = (
    "Barrel rate",
    "Exit velocity",
    "Ideal attack angle",
    "Pull air",
)

# The three absence states, each its own fixed text. Never blank, never a
# number, never each other.
ABSENCE_TEXT: dict[AbsenceReason, str] = {
    AbsenceReason.NOT_APPLICABLE: "not applicable",
    AbsenceReason.NOT_YET_OBSERVED: "not yet observed",
    AbsenceReason.SOURCE_UNAVAILABLE: "source unavailable",
}

# Muted, non-green, mutually distinct styles per absence state.
_ABSENCE_CSS: dict[AbsenceReason, str] = {
    AbsenceReason.NOT_APPLICABLE: ("color: #495057; background-color: #e9ecef; font-style: italic"),
    AbsenceReason.NOT_YET_OBSERVED: (
        "color: #664d03; background-color: #fff3cd; font-style: italic"
    ),
    AbsenceReason.SOURCE_UNAVAILABLE: (
        "color: #58151c; background-color: #f8d7da; font-style: italic"
    ),
}

# Density presets: rows in view before the component scrolls (see module
# docstring for the 1.37-floor constraint this encodes).
DENSITY_ROWS: dict[str, int] = {"Compact": 4, "Cozy": 8, "Roomy": 14}

_ROW_PX = 35
_HEADER_PX = 38


def _sorted_batters(snapshot: InputSnapshot) -> list[BatterInputs]:
    """Neutral identity order: name ascending, id as the deterministic tie-break."""
    return sorted(snapshot.batters, key=lambda b: (b.name, b.batter_id))


def row_batter_ids(snapshot: InputSnapshot) -> tuple[str, ...]:
    """Batter ids in grid row order — the selection layer's positional map."""
    return tuple(batter.batter_id for batter in _sorted_batters(snapshot))


def _metric_fields(
    metrics: WindowedBatterMetrics,
) -> dict[
    str,
    SnapshotField[BattedBallRate]
    | SnapshotField[ExitVelocityAverage]
    | SnapshotField[SwingShare]
    | SnapshotField[AirBallShare],
]:
    return {
        "Barrel rate": metrics.barrel_rate,
        "Exit velocity": metrics.exit_velocity,
        "Ideal attack angle": metrics.ideal_attack_angle_share,
        "Pull air": metrics.pull_air_share,
    }


def _display_text(
    field: SnapshotField[BattedBallRate]
    | SnapshotField[ExitVelocityAverage]
    | SnapshotField[SwingShare]
    | SnapshotField[AirBallShare],
) -> str:
    """The cell text: value with its sample beside it (D-014), or absence text."""
    value = field.value
    if value is None:
        assert field.absence is not None  # the contract's exactly-one law
        return ABSENCE_TEXT[field.absence]
    if isinstance(value, BattedBallRate):
        return f"{value.rate} · BBE {value.batted_ball_events}"
    if isinstance(value, ExitVelocityAverage):
        return f"{value.miles_per_hour} mph · BBE {value.batted_ball_events}"
    if isinstance(value, SwingShare):
        return f"{value.share} · swings {value.tracked_swings}"
    return f"{value.share} · air balls {value.air_balls}"


def _numeric(
    field: SnapshotField[BattedBallRate]
    | SnapshotField[ExitVelocityAverage]
    | SnapshotField[SwingShare]
    | SnapshotField[AirBallShare],
) -> Decimal | None:
    """The gradable magnitude of a present value; ``None`` for any absence."""
    value = field.value
    if value is None:
        return None
    if isinstance(value, BattedBallRate):
        return value.rate
    if isinstance(value, ExitVelocityAverage):
        return value.miles_per_hour
    return value.share


def grid_frame(snapshot: InputSnapshot, window: Window) -> pd.DataFrame:
    """The display frame: one row per batter, identity plus the four metrics."""
    rows = []
    for batter in _sorted_batters(snapshot):
        metrics = batter.metrics_for(window)
        row: dict[str, str] = {BATTER_COLUMN: batter.name}
        for column, field in _metric_fields(metrics).items():
            row[column] = _display_text(field)
        rows.append(row)
    return pd.DataFrame(rows, columns=[BATTER_COLUMN, *METRIC_COLUMNS])


def state_frame(snapshot: InputSnapshot, window: Window) -> pd.DataFrame:
    """The display-state tokens behind each cell — the testable semantics."""
    rows = []
    for batter in _sorted_batters(snapshot):
        metrics = batter.metrics_for(window)
        row: dict[str, str] = {BATTER_COLUMN: "identity"}
        for column, field in _metric_fields(metrics).items():
            row[column] = field.display_state().value
        rows.append(row)
    return pd.DataFrame(rows, columns=[BATTER_COLUMN, *METRIC_COLUMNS])


def _green(intensity: float) -> str:
    """Hand-rolled green-is-good scale: 0.0 = palest, 1.0 = strongest."""
    clamped = min(max(intensity, 0.0), 1.0)
    red = round(233 - 122 * clamped)
    green = round(247 - 64 * clamped)
    blue = round(233 - 112 * clamped)
    return f"color: #0a3622; background-color: rgb({red}, {green}, {blue})"


def style_lookup(snapshot: InputSnapshot, window: Window) -> dict[str, dict[str, str]]:
    """Per-column map from rendered cell text to its inline CSS.

    Present values are graded on a column-normalised green scale — a lone
    present value grades mid-scale rather than dividing by zero spread. Each
    absence state maps to its own fixed, non-green style. Identity cells carry
    no style. Two batters with identical cell text share a grade by
    construction: same text means same value and same sample.
    """
    batters = _sorted_batters(snapshot)
    lookup: dict[str, dict[str, str]] = {BATTER_COLUMN: {}}
    for column in METRIC_COLUMNS:
        fields = [_metric_fields(b.metrics_for(window))[column] for b in batters]
        numerics = [_numeric(field) for field in fields]
        present = [float(n) for n in numerics if n is not None]
        low, high = (min(present), max(present)) if present else (0.0, 0.0)
        spread = high - low
        column_map: dict[str, str] = {}
        for field, numeric in zip(fields, numerics, strict=True):
            text = _display_text(field)
            if numeric is None:
                assert field.absence is not None
                column_map[text] = _ABSENCE_CSS[field.absence]
            elif spread == 0.0:
                column_map[text] = _green(0.5)
            else:
                column_map[text] = _green((float(numeric) - low) / spread)
        lookup[column] = column_map
    return lookup


def graded_styler(display: pd.DataFrame, lookup: dict[str, dict[str, str]]) -> Styler:
    """The ``Styler.map`` application (D-059): one lookup per column, no matplotlib."""
    styler = display.style
    for column in display.columns:
        column_map = lookup.get(str(column), {})
        styler = styler.map(
            lambda text, m=column_map: m.get(str(text), ""),
            subset=[column],
        )
    return styler


def visible_columns(chosen_metrics: tuple[str, ...]) -> list[str]:
    """The identity column always shows (selection stays readable); chosen
    metrics follow in canonical order regardless of pick order."""
    return [BATTER_COLUMN, *[c for c in METRIC_COLUMNS if c in chosen_metrics]]


def frame_height(density: str, row_count: int) -> int:
    """Component height for a density preset: rows-in-view, capped at the data."""
    rows_in_view = DENSITY_ROWS[density]
    return _HEADER_PX + _ROW_PX * min(rows_in_view, max(row_count, 1)) + 3
