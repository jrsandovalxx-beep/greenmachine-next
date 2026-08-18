"""The §GMF-004 parks screen: venues down, conditions across.

Built on the §GMF-002 grid by import, like §GMF-003 before it. The two park
factor columns are numeric, graded and sortable through the grid's own
row-agnostic builders — one copy of the grading mechanism in the repository,
and this is still not it. What this module adds is the row source (venues),
the column set, and the D-055 rendering policy criterion 4 requires.

**Two kinds of column, and the difference is load-bearing.**

- The **factor columns** carry ``ParkFactor`` values: a magnitude the component
  can sort and the green scale can grade, with each value's plate-appearance
  sample beside it (D-014). They ride the numeric frame, so an absent factor
  is a missing value there and the deployed component renders it as its own
  ``None`` — the recorded GMF-002 defect. The remedy is the authorized additive
  one: `factor_absence_notes` states each absent factor's reason in words
  beneath the table. The grid's cell representation is untouched.
- The **condition columns** — team, venue type, roof, forecast — are ordinary
  text in the frame itself. They are not metrics: a roof state has no
  magnitude, and forcing one through the numeric frame would either invent a
  ranking for it or make a present value indistinguishable from an absent one.
  Because their words live in the frame rather than in a ``Styler`` display
  value, they are immune to the ``None``-cell defect by construction, which is
  why criterion 4's three roof states can be read directly off the table.

**No ranking, no targeting.** The ticket is named "parks to target" and the
register forbids the product doing the targeting (D-015/D-017): rows arrive in
neutral identity order — the venue's own name — with no score, no factor
ordering, and nothing pre-selected. Sorting by a factor is one click in the
column header and belongs to the user, exactly as on the batter grid.

**Two provenances, never blurred.** The factor columns render the pinned
manual export with its date; the roof and forecast columns render a fixture
binding, with §GMF-005 named as where a live weather source arrives. The page
says which is which, because a screen that mixed real and fixture data
silently would be the most expensive kind of correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

import pandas as pd

from greenmachine.grid import (
    FieldRow,
    MetricField,
    cell_text,
    display_state_frame,
    numeric_frame,
    style_frame_for,
    text_frame,
)
from greenmachine.inputs import (
    AbsenceReason,
    Handedness,
    InputSnapshot,
    ParkInputs,
    RoofStatus,
    VenueType,
)

VENUE_COLUMN = "Venue"
TEAM_COLUMN = "Team"
VENUE_TYPE_COLUMN = "Venue type"
LHB_FACTOR_COLUMN = "HR factor (LHB)"
RHB_FACTOR_COLUMN = "HR factor (RHB)"
ROOF_COLUMN = "Roof"
FORECAST_COLUMN = "Forecast"

# The graded, sortable columns — the only ones that reach the grid machinery.
FACTOR_COLUMNS: tuple[str, ...] = (LHB_FACTOR_COLUMN, RHB_FACTOR_COLUMN)

# The text columns, carried in the frame as words.
CONDITION_COLUMNS: tuple[str, ...] = (TEAM_COLUMN, VENUE_TYPE_COLUMN, ROOF_COLUMN, FORECAST_COLUMN)

# Display order: venue type sits immediately before the factors, so criterion
# 2's "per handedness beside venue type" is true of the rendered row and not
# only of the data behind it.
ALL_COLUMNS: tuple[str, ...] = (
    TEAM_COLUMN,
    VENUE_TYPE_COLUMN,
    LHB_FACTOR_COLUMN,
    RHB_FACTOR_COLUMN,
    ROOF_COLUMN,
    FORECAST_COLUMN,
)

FACTOR_COLUMN_SIDES: dict[str, Handedness] = {
    LHB_FACTOR_COLUMN: Handedness.LEFT,
    RHB_FACTOR_COLUMN: Handedness.RIGHT,
}

# Venue type in the user's words. Never bare "not applicable" for the roof of
# an open-air park: the difference between "there is no roof" and "the roof is
# always shut" decides whether a forecast means anything, and collapsing both
# into the contract's NOT_APPLICABLE would hide exactly that.
VENUE_TYPE_WORDS: dict[VenueType, str] = {
    VenueType.OPEN_AIR: "open air",
    VenueType.FIXED_ROOF: "fixed roof",
    VenueType.RETRACTABLE_ROOF: "retractable roof",
}

ROOF_STATUS_WORDS: dict[RoofStatus, str] = {
    RoofStatus.OPEN: "retractable — open",
    RoofStatus.CLOSED: "retractable — closed",
    RoofStatus.UNKNOWN: "retractable — state unknown",
}

ABSENCE_WORDS: dict[AbsenceReason, str] = {
    AbsenceReason.NOT_APPLICABLE: "not applicable to this venue",
    AbsenceReason.NOT_YET_OBSERVED: (
        "not yet observed — the source answered, nothing has accumulated"
    ),
    AbsenceReason.SOURCE_UNAVAILABLE: (
        "source unavailable — the source was consulted and did not answer"
    ),
}


@unique
class ForecastDisposition(Enum):
    """Whether a forecast may be printed for a venue, and why not when not.

    Total over every venue type and roof state the contract can construct.
    """

    APPLIES = "applies"
    SUPPRESSED_CLOSED_ROOF = "suppressed_closed_roof"
    WITHHELD_ROOF_UNDETERMINED = "withheld_roof_undetermined"


def venue_type_text(park: ParkInputs) -> str:
    return VENUE_TYPE_WORDS[park.venue.venue_type]


def roof_text(park: ParkInputs) -> str:
    """The roof cell: D-055's three states, each visibly its own.

    A venue with no roof and a venue permanently under one both carry
    ``NOT_APPLICABLE`` in the contract — correctly, since neither has a roof
    *state* to observe — so this cell names the venue type rather than printing
    the shared absence reason twice and losing the distinction.
    """
    status = park.roof_status.value
    if status is not None:
        return ROOF_STATUS_WORDS[status]
    if park.venue.venue_type is VenueType.OPEN_AIR:
        return "none — open air"
    if park.venue.venue_type is VenueType.FIXED_ROOF:
        return "fixed — permanently closed"
    assert park.roof_status.absence is not None  # the contract's exactly-one law
    return f"retractable — {ABSENCE_WORDS[park.roof_status.absence]}"


def forecast_disposition(park: ParkInputs) -> ForecastDisposition:
    """Criterion 4's rule, as a decision separate from its wording.

    A forecast is never printed for a closed roof, and — the ruling this screen
    adds — never printed when the roof state is *undetermined*. An unknown roof
    may in fact be shut, so printing under UNKNOWN risks printing a forecast for
    a closed roof, the exact thing the criterion forbids; withholding is the
    only rendering that is correct under both resolutions. The same argument
    covers a roof state the source never supplied, so those absences withhold
    too rather than defaulting to "print it".
    """
    venue_type = park.venue.venue_type
    if venue_type is VenueType.FIXED_ROOF:
        return ForecastDisposition.SUPPRESSED_CLOSED_ROOF
    if venue_type is VenueType.OPEN_AIR:
        return ForecastDisposition.APPLIES
    status = park.roof_status.value
    if status is RoofStatus.OPEN:
        return ForecastDisposition.APPLIES
    if status is RoofStatus.CLOSED:
        return ForecastDisposition.SUPPRESSED_CLOSED_ROOF
    return ForecastDisposition.WITHHELD_ROOF_UNDETERMINED


def forecast_value_text(park: ParkInputs) -> str:
    """The forecast itself, in the user's units — or its absence in words."""
    forecast = park.forecast.value
    if forecast is None:
        assert park.forecast.absence is not None  # the contract's exactly-one law
        return ABSENCE_WORDS[park.forecast.absence]
    return (
        f"{forecast.temperature_f} °F · wind {forecast.wind_speed_mph} mph "
        f"{forecast.wind_direction} · {forecast.short_forecast}"
    )


def forecast_text(park: ParkInputs) -> str:
    """The forecast cell: the values, or the stated reason they are not shown.

    Suppression and withholding never print the numbers — not greyed, not
    parenthesised, not "for reference". A forecast on screen beside a closed
    roof is a claim about conditions of play, and the criterion's word is
    *never*.
    """
    disposition = forecast_disposition(park)
    if disposition is ForecastDisposition.SUPPRESSED_CLOSED_ROOF:
        if park.venue.venue_type is VenueType.FIXED_ROOF:
            return "not shown — fixed roof, play is indoors"
        return "not shown — roof closed, play is indoors"
    if disposition is ForecastDisposition.WITHHELD_ROOF_UNDETERMINED:
        return "not shown — roof state undetermined, so applicability is unknown"
    return forecast_value_text(park)


def park_factor_fields(park: ParkInputs) -> dict[str, MetricField]:
    """One venue's two factor fields, keyed by their column names."""
    return {
        LHB_FACTOR_COLUMN: park.park_factor_lhb,
        RHB_FACTOR_COLUMN: park.park_factor_rhb,
    }


def ordered_parks(snapshot: InputSnapshot) -> tuple[ParkInputs, ...]:
    """Neutral identity order: venue name ascending, slug as the tie-break.

    Never factor order. Ordering venues by a park factor would be the product
    naming which parks to target, which is the user's judgement to make and
    D-015/D-017's line.
    """
    return tuple(sorted(snapshot.parks, key=lambda park: (park.venue.name, park.venue.venue_id)))


def screen_rows(snapshot: InputSnapshot) -> list[FieldRow]:
    """The venues as grid rows — identity text and the two factor fields."""
    return [(park.venue.name, park_factor_fields(park)) for park in ordered_parks(snapshot)]


@dataclass(frozen=True)
class ParksScreen:
    """The three frames the component receives, assembled once.

    ``data`` carries the condition columns as text beside the numeric factor
    columns; ``texts`` and ``styles`` cover the factor columns only, which is
    exactly the subset `graded_styler` is asked to format and style. A text
    column left out of that subset renders its own frame value, so the roof and
    forecast words reach the canvas without passing through the null-cell path.
    """

    data: pd.DataFrame
    texts: pd.DataFrame
    styles: pd.DataFrame


def screen_frames(snapshot: InputSnapshot) -> ParksScreen:
    rows = screen_rows(snapshot)
    parks = ordered_parks(snapshot)
    data = numeric_frame(rows, VENUE_COLUMN, FACTOR_COLUMNS)
    position = 1
    for column, values in (
        (TEAM_COLUMN, [park.venue.team for park in parks]),
        (VENUE_TYPE_COLUMN, [venue_type_text(park) for park in parks]),
    ):
        data.insert(position, column, values)
        position += 1
    data[ROOF_COLUMN] = [roof_text(park) for park in parks]
    data[FORECAST_COLUMN] = [forecast_text(park) for park in parks]
    return ParksScreen(
        data=data,
        texts=text_frame(rows, VENUE_COLUMN, FACTOR_COLUMNS),
        styles=style_frame_for(rows, VENUE_COLUMN, FACTOR_COLUMNS),
    )


def screen_state_frame(snapshot: InputSnapshot) -> pd.DataFrame:
    """The display-state tokens behind each factor cell — testable semantics."""
    return display_state_frame(screen_rows(snapshot), VENUE_COLUMN, FACTOR_COLUMNS)


def factor_absence_notes(snapshot: InputSnapshot) -> tuple[str, ...]:
    """Every absent park factor, named with its venue, side and reason.

    The authorized additive remedy for the recorded GMF-002 defect: the
    deployed component renders a null-data cell as its own ``None`` and drops
    the display value carried for it, so a factor cell that correctly says
    "not yet observed" reads as ``None`` on the canvas. This is where the
    reason can be read. The condition columns need no such note — their words
    are in the frame, not in a display value.
    """
    notes: list[str] = []
    for park in ordered_parks(snapshot):
        missing = [
            f"{column} ({ABSENCE_WORDS[field.absence]})"
            for column, field in park_factor_fields(park).items()
            if field.absence is not None
        ]
        if missing:
            notes.append(f"{park.venue.name} — {'; '.join(missing)}")
    return tuple(notes)


def forecast_suppression_notes(snapshot: InputSnapshot) -> tuple[str, ...]:
    """Every venue whose forecast is not printed, and exactly why.

    Criterion 4 in words as well as in cells: a suppressed forecast is
    acknowledged by name, never silently blank. The two reasons stay apart —
    a closed roof is a known state that makes weather irrelevant, while an
    undetermined roof is an unknown that makes relevance unknowable.
    """
    closed: list[str] = []
    withheld: list[str] = []
    for park in ordered_parks(snapshot):
        disposition = forecast_disposition(park)
        if disposition is ForecastDisposition.SUPPRESSED_CLOSED_ROOF:
            closed.append(f"{park.venue.name} ({venue_type_text(park)})")
        elif disposition is ForecastDisposition.WITHHELD_ROOF_UNDETERMINED:
            withheld.append(f"{park.venue.name} ({roof_text(park)})")
    notes: list[str] = []
    if closed:
        notes.append(
            f"Forecast not printed — play is under a closed roof ({len(closed)}): "
            f"{', '.join(closed)}."
        )
    if withheld:
        notes.append(
            f"Forecast withheld — the roof state is undetermined, so a forecast "
            f"might describe a closed park ({len(withheld)}): {', '.join(withheld)}."
        )
    return tuple(notes)


def unavailable_forecast_notes(snapshot: InputSnapshot) -> tuple[str, ...]:
    """Venues where the forecast applies but the adapter had no value.

    Criterion 3's *unavailable* path, stated rather than left as a bare cell:
    the roof does not suppress it and the adapter still did not answer, which
    is a fact about the source and not about the ballpark.
    """
    return tuple(
        f"{park.venue.name} — {ABSENCE_WORDS[park.forecast.absence]}"
        for park in ordered_parks(snapshot)
        if forecast_disposition(park) is ForecastDisposition.APPLIES
        and park.forecast.absence is not None
    )


def factor_detail_notes(park: ParkInputs) -> tuple[str, ...]:
    """One venue's factor cells in words — value with its sample, or reason."""
    return tuple(
        f"{column} — {cell_text(field)}" for column, field in park_factor_fields(park).items()
    )
