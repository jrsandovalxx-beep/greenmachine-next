"""Display frames and hand-rolled ``Styler`` grading for the grid (GMF-002).

The contract enforces the semantics; this module's obligation is to keep them
visible at render:

- **Absence is never a blank.** Each absence state renders as its own fixed
  text — ``not applicable`` / ``not yet observed`` / ``source unavailable`` —
  visibly distinct from numeric zero and from each other. A numeric zero
  renders as a number with its sample beside it (D-014), never as an empty
  cell.
- **Metric columns are numeric so the component sorts numerically.** The data
  frame carries raw ``float`` values (absences as missing); the rendered text
  rides the ``Styler`` as display values — probed: the component receives the
  raw data and the display values as separate payloads and sorts on the data,
  so ``950.5`` orders below ``1000.5`` where their display strings would not.
- **Grading is hand-rolled via ``Styler.map`` (D-059)** — a per-cell inline
  CSS application. Present values get a green-is-good scale normalised within
  their column; each absence state gets its own muted, non-green style. No
  matplotlib anywhere.
- **The initial row order is neutral and deliberate**: batter name ascending —
  an identity order, not a metric. Every metric ordering is user-initiated in
  the component itself (*sort, don't blend*, D-015/D-017).
- **Density at the 1.37 floor**: ``st.dataframe`` exposes no row-height
  control at the version floor (D-062), so density is implemented as a
  rows-in-view viewport preset — the closest control the floor offers, named
  for what it is.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from functools import partial
from typing import TYPE_CHECKING, Any

import pandas as pd

from greenmachine.inputs import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    BatterInputs,
    ExitVelocityAverage,
    ExpectedWeightedOnBase,
    InputSnapshot,
    IsolatedPower,
    ParkFactor,
    SnapshotField,
    SwingingStrikeRate,
    SwingShare,
    UsageShare,
    WhiffRate,
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


# A metric cell's field. ``Any`` rather than a union of nine concrete
# ``SnapshotField`` instantiations: the generic frame builders carry rows whose
# columns hold different value types at once, and ``SnapshotField`` is invariant,
# so no union admits them together. The looseness is repaid immediately — the
# value dispatch below is total and raises on a type it does not know.
MetricField = SnapshotField[Any]

# One row for the frame builders: its identity text, and its columns' fields.
# This is the whole of what a grid row is, which is why one set of builders
# serves batters keyed by window and pitch types keyed by usage alike.
FieldRow = tuple[str, dict[str, MetricField]]


def metric_fields(metrics: WindowedBatterMetrics) -> dict[str, MetricField]:
    return {
        "Barrel rate": metrics.barrel_rate,
        "Exit velocity": metrics.exit_velocity,
        "Ideal attack angle": metrics.ideal_attack_angle_share,
        "Pull air": metrics.pull_air_share,
    }


def cell_text(field: MetricField) -> str:
    """The cell text: value with its sample beside it (D-014), or absence text.

    Every branch names the denominator the number is over, because two metrics
    on the GMF-003 surface share a numerator and differ only in denominator
    (whiff rate over swings, swinging-strike rate over pitches of that type) and
    a third divides by a different population again (usage, over every tracked
    pitch of every type). A cell that printed a bare share would leave those
    three indistinguishable.

    The dispatch is total and raises on an unrecognised type. It previously fell
    through to ``AirBallShare``'s format, which meant a value type nobody had
    considered would render as an air-ball share rather than fail — the exact
    trap this surface's near-identical denominators set.
    """
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
    if isinstance(value, AirBallShare):
        return f"{value.share} · air balls {value.air_balls}"
    if isinstance(value, UsageShare):
        return f"{value.share} · {value.sample_pitches} pitches, all types"
    if isinstance(value, IsolatedPower):
        return f"{value.points} · AB {value.at_bats}"
    if isinstance(value, ExpectedWeightedOnBase):
        return f"{value.value} · PA {value.plate_appearances}"
    if isinstance(value, ParkFactor):
        # An index, not a rate: 100 is neutral and the number has no
        # denominator of its own. ``PA`` here is the sample the factor was
        # built over (D-014 beside the value), which varies from 13,560 to
        # 31,517 across the pinned export — a spread a reader must see.
        return f"{value.factor} · PA {value.plate_appearances}"
    if isinstance(value, WhiffRate):
        return f"{value.rate} · {value.swings} swings"
    if isinstance(value, SwingingStrikeRate):
        return f"{value.rate} · {value.pitches} pitches, this type"
    raise TypeError(  # no silent fall-through onto another metric's format
        f"no display format for value type {type(value).__name__!r}: a metric "
        "renders with its own denominator named, or it does not render"
    )


def _numeric(field: MetricField) -> Decimal | None:
    """The gradable magnitude of a present value; ``None`` for any absence.

    Total for the same reason ``cell_text`` is: the old trailing
    ``value.share`` silently claimed every unrecognised type had a ``share``
    attribute meaning the same thing.
    """
    value = field.value
    if value is None:
        return None
    if isinstance(value, BattedBallRate):
        return value.rate
    if isinstance(value, ExitVelocityAverage):
        return value.miles_per_hour
    if isinstance(value, SwingShare | AirBallShare | UsageShare):
        return value.share
    if isinstance(value, IsolatedPower):
        return value.points
    if isinstance(value, ExpectedWeightedOnBase):
        return value.value
    if isinstance(value, ParkFactor):
        return value.factor
    if isinstance(value, WhiffRate | SwingingStrikeRate):
        return value.rate
    raise TypeError(f"no gradable magnitude for value type {type(value).__name__!r}")


def _batter_rows(snapshot: InputSnapshot, window: Window) -> list[FieldRow]:
    """The batter grid's rows, in neutral identity order."""
    return [
        (batter.name, metric_fields(batter.metrics_for(window)))
        for batter in _sorted_batters(snapshot)
    ]


def numeric_frame(
    rows: Sequence[FieldRow], identity_column: str, columns: Sequence[str]
) -> pd.DataFrame:
    """The data frame the component sorts on: identity as text, metrics as
    raw ``float`` columns with absences as missing values. Rendered text is
    the ``Styler``'s job (`text_frame` / `graded_styler`), never this
    frame's — a string metric column would sort lexicographically."""
    built: list[dict[str, object]] = []
    for identity, fields_by_column in rows:
        row: dict[str, object] = {identity_column: identity}
        for column in columns:
            numeric = _numeric(fields_by_column[column])
            row[column] = float(numeric) if numeric is not None else None
        built.append(row)
    frame = pd.DataFrame(built, columns=[identity_column, *columns])
    return frame.astype(dict.fromkeys(columns, "float64"))


def text_frame(
    rows: Sequence[FieldRow], identity_column: str, columns: Sequence[str]
) -> pd.DataFrame:
    """Every cell's rendered text: value with its sample beside it (D-014),
    or the absence text — never blank, never a bare number without its
    sample. These ride the ``Styler`` as display values over `numeric_frame`'s
    numeric data."""
    built = []
    for identity, fields_by_column in rows:
        row: dict[str, str] = {identity_column: identity}
        for column in columns:
            row[column] = cell_text(fields_by_column[column])
        built.append(row)
    return pd.DataFrame(built, columns=[identity_column, *columns])


def display_state_frame(
    rows: Sequence[FieldRow], identity_column: str, columns: Sequence[str]
) -> pd.DataFrame:
    """The display-state tokens behind each cell — the testable semantics."""
    built = []
    for _identity, fields_by_column in rows:
        row: dict[str, str] = {identity_column: "identity"}
        for column in columns:
            row[column] = fields_by_column[column].display_state().value
        built.append(row)
    return pd.DataFrame(built, columns=[identity_column, *columns])


def grid_frame(snapshot: InputSnapshot, window: Window) -> pd.DataFrame:
    """The batter grid's numeric frame. Unchanged in behaviour: the row source
    moved out, the assembly did not."""
    return numeric_frame(_batter_rows(snapshot, window), BATTER_COLUMN, METRIC_COLUMNS)


def display_texts(snapshot: InputSnapshot, window: Window) -> pd.DataFrame:
    """The batter grid's cell texts."""
    return text_frame(_batter_rows(snapshot, window), BATTER_COLUMN, METRIC_COLUMNS)


def state_frame(snapshot: InputSnapshot, window: Window) -> pd.DataFrame:
    """The batter grid's display-state tokens."""
    return display_state_frame(_batter_rows(snapshot, window), BATTER_COLUMN, METRIC_COLUMNS)


def _fixed_text(text: str, _value: object) -> str:
    """A constant per-cell formatter: the display text, whatever the value."""
    return text


def _green(intensity: float) -> str:
    """Hand-rolled green-is-good scale: 0.0 = palest, 1.0 = strongest."""
    clamped = min(max(intensity, 0.0), 1.0)
    red = round(233 - 122 * clamped)
    green = round(247 - 64 * clamped)
    blue = round(233 - 112 * clamped)
    return f"color: #0a3622; background-color: rgb({red}, {green}, {blue})"


def style_frame_for(
    rows: Sequence[FieldRow], identity_column: str, columns: Sequence[str]
) -> pd.DataFrame:
    """Per-cell inline CSS, positionally aligned with `numeric_frame`.

    Present values grade on a column-normalised green scale — a lone present
    value grades mid-scale rather than dividing by zero spread. Each absence
    state carries its own fixed, non-green style, applied by position: a
    numeric frame cannot key styles by cell text, because every absence is
    the same missing value. Identity cells carry no style.
    """
    built: list[dict[str, str]] = [{identity_column: ""} for _ in rows]
    for column in columns:
        fields = [fields_by_column[column] for _identity, fields_by_column in rows]
        numerics = [_numeric(field) for field in fields]
        present = [float(n) for n in numerics if n is not None]
        low, high = (min(present), max(present)) if present else (0.0, 0.0)
        spread = high - low
        for row, field, numeric in zip(built, fields, numerics, strict=True):
            if numeric is None:
                assert field.absence is not None  # the contract's exactly-one law
                row[column] = _ABSENCE_CSS[field.absence]
            elif spread == 0.0:
                row[column] = _green(0.5)
            else:
                row[column] = _green((float(numeric) - low) / spread)
    return pd.DataFrame(built, columns=[identity_column, *columns])


def style_frame(snapshot: InputSnapshot, window: Window) -> pd.DataFrame:
    """The batter grid's per-cell CSS."""
    return style_frame_for(_batter_rows(snapshot, window), BATTER_COLUMN, METRIC_COLUMNS)


def graded_styler(
    numeric: pd.DataFrame,
    texts: pd.DataFrame,
    styles: pd.DataFrame,
    columns: Sequence[str] = METRIC_COLUMNS,
) -> Styler:
    """The ``Styler`` over the numeric frame: per-cell display text via
    ``format`` (an absent cell's text is its reason, applied as that cell's
    ``na_rep``) and per-cell CSS via ``Styler.map`` (D-059). Per-cell subsets
    keep text and style exact even when two cells share a value with
    different samples.

    ``columns`` defaults to the batter grid's four metric columns, which is
    what this function iterated before it took the parameter at all.
    """
    styler = numeric.style
    for row in range(len(numeric)):
        for column in columns:
            # The runtime accepts a (rows, columns) subset tuple; the stubs
            # model a narrower union, so the slice is typed Any deliberately.
            cell: Any = pd.IndexSlice[[row], [column]]
            text = str(texts.at[row, column])
            if pd.isna(numeric.at[row, column]):
                styler = styler.format(na_rep=text, subset=cell)
            else:
                styler = styler.format(partial(_fixed_text, text), subset=cell)
            css = str(styles.at[row, column])
            if css:
                styler = styler.map(lambda _v, c=css: c, subset=cell)
    return styler


def visible_columns(
    chosen_metrics: tuple[str, ...],
    identity_column: str = BATTER_COLUMN,
    columns: Sequence[str] = METRIC_COLUMNS,
) -> list[str]:
    """The identity column always shows (selection stays readable); chosen
    metrics follow in canonical order regardless of pick order.

    The defaults are the batter grid's own identity column and metric set —
    the exact values this function closed over before it took parameters.
    """
    return [identity_column, *[c for c in columns if c in chosen_metrics]]


def frame_height(density: str, row_count: int) -> int:
    """Component height for a density preset: rows-in-view, capped at the data."""
    rows_in_view = DENSITY_ROWS[density]
    return _HEADER_PX + _ROW_PX * min(rows_in_view, max(row_count, 1)) + 3
