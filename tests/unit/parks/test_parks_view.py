"""GMF-004 criteria 2-4: the parks screen's rendering policy, as behaviour.

Fixtures here are synthetic venues (D-052): no provider table is pasted into a
test, and the values are deliberately non-baseball. The pinned export is
exercised where it belongs — in the reader's own tests and in the composed
snapshot — never copied into a fixture.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from greenmachine.inputs import (
    AbsenceReason,
    DisplayState,
    Handedness,
    InputSnapshot,
    ParkFactor,
    ParkInputs,
    ParkVenue,
    RoofStatus,
    SnapshotField,
    SourceKind,
    SourceRecord,
    VenueType,
    WeatherForecast,
)
from greenmachine.parks import (
    ALL_COLUMNS,
    FACTOR_COLUMNS,
    FORECAST_COLUMN,
    LHB_FACTOR_COLUMN,
    RHB_FACTOR_COLUMN,
    ROOF_COLUMN,
    TEAM_COLUMN,
    VENUE_COLUMN,
    VENUE_TYPE_COLUMN,
    ForecastDisposition,
    factor_absence_notes,
    factor_detail_notes,
    forecast_disposition,
    forecast_suppression_notes,
    forecast_text,
    ordered_parks,
    roof_text,
    screen_frames,
    screen_state_frame,
    unavailable_forecast_notes,
)

SOURCE_ID = "parks-view-synthetic"

_SOURCES = (
    SourceRecord(
        source_id=SOURCE_ID,
        kind=SourceKind.SYNTHETIC,
        description="parks view test values - deliberately non-baseball (OQ-4)",
    ),
)

_OBTAINED_AT = datetime(2026, 1, 1, 11, 30, 0, tzinfo=UTC)

_FORECAST = WeatherForecast(
    temperature_f=Decimal("222.2"),
    wind_speed_mph=Decimal("77.7"),
    wind_direction="SSW",
    short_forecast="Synthetic",
    obtained_at=_OBTAINED_AT,
)


def _venue(slug: str, name: str, venue_type: VenueType, team: str = "Club Alpha") -> ParkVenue:
    return ParkVenue(
        slug,
        name,
        team,
        venue_type,
        savant_venue_id=None,
        latitude=Decimal("10.000"),
        longitude=Decimal("-20.000"),
    )


def _factor(value: str, side: Handedness, sample: int = 5000) -> SnapshotField[ParkFactor]:
    return SnapshotField.present(
        ParkFactor(factor=Decimal(value), handedness=side, plate_appearances=sample), SOURCE_ID
    )


def _absent_factor(reason: AbsenceReason) -> SnapshotField[ParkFactor]:
    return SnapshotField[ParkFactor].absent(reason, SOURCE_ID)


def _park(
    venue: ParkVenue,
    *,
    lhb: SnapshotField[ParkFactor] | None = None,
    rhb: SnapshotField[ParkFactor] | None = None,
    roof: SnapshotField[RoofStatus] | None = None,
    forecast: SnapshotField[WeatherForecast] | None = None,
) -> ParkInputs:
    if roof is None:
        roof = (
            SnapshotField.present(RoofStatus.OPEN, SOURCE_ID)
            if venue.venue_type is VenueType.RETRACTABLE_ROOF
            else SnapshotField[RoofStatus].absent(AbsenceReason.NOT_APPLICABLE)
        )
    return ParkInputs(
        venue=venue,
        park_factor_lhb=lhb if lhb is not None else _factor("110", Handedness.LEFT),
        park_factor_rhb=rhb if rhb is not None else _factor("90", Handedness.RIGHT),
        roof_status=roof,
        forecast=forecast if forecast is not None else SnapshotField.present(_FORECAST, SOURCE_ID),
    )


def _snapshot(*parks: ParkInputs) -> InputSnapshot:
    return InputSnapshot(
        captured_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        sources=_SOURCES,
        batters=(),
        parks=parks,
    )


# --- criterion 4: the three roof states, each visibly its own ---------------


def test_open_air_and_fixed_roof_do_not_render_the_same_words() -> None:
    """Both carry NOT_APPLICABLE in the contract; collapsing them on screen
    would hide the one distinction that decides whether weather matters."""
    open_air = roof_text(_park(_venue("a", "Alpha Park", VenueType.OPEN_AIR)))
    fixed = roof_text(_park(_venue("b", "Bravo Dome", VenueType.FIXED_ROOF)))
    assert open_air != fixed
    assert "open air" in open_air
    assert "closed" in fixed


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (RoofStatus.OPEN, "open"),
        (RoofStatus.CLOSED, "closed"),
        (RoofStatus.UNKNOWN, "unknown"),
    ],
)
def test_each_retractable_state_renders_distinctly(status: RoofStatus, expected: str) -> None:
    park = _park(
        _venue("c", "Charlie Field", VenueType.RETRACTABLE_ROOF),
        roof=SnapshotField.present(status, SOURCE_ID),
    )
    assert expected in roof_text(park)


def test_the_three_retractable_states_are_mutually_distinct() -> None:
    texts = {
        roof_text(
            _park(
                _venue("c", "Charlie Field", VenueType.RETRACTABLE_ROOF),
                roof=SnapshotField.present(status, SOURCE_ID),
            )
        )
        for status in RoofStatus
    }
    assert len(texts) == 3


# --- criterion 4: a forecast is never printed for a closed roof -------------


def test_a_fixed_roof_never_prints_the_forecast() -> None:
    park = _park(_venue("b", "Bravo Dome", VenueType.FIXED_ROOF))
    assert forecast_disposition(park) is ForecastDisposition.SUPPRESSED_CLOSED_ROOF
    text = forecast_text(park)
    assert "not shown" in text
    assert str(_FORECAST.temperature_f) not in text
    assert str(_FORECAST.wind_speed_mph) not in text


def test_a_closed_retractable_roof_never_prints_the_forecast() -> None:
    park = _park(
        _venue("c", "Charlie Field", VenueType.RETRACTABLE_ROOF),
        roof=SnapshotField.present(RoofStatus.CLOSED, SOURCE_ID),
    )
    assert forecast_disposition(park) is ForecastDisposition.SUPPRESSED_CLOSED_ROOF
    assert str(_FORECAST.temperature_f) not in forecast_text(park)


@pytest.mark.parametrize(
    "roof",
    [
        SnapshotField.present(RoofStatus.UNKNOWN, SOURCE_ID),
        SnapshotField[RoofStatus].absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID),
        SnapshotField[RoofStatus].absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID),
    ],
)
def test_an_undetermined_roof_withholds_the_forecast(roof: SnapshotField[RoofStatus]) -> None:
    """The ratified Q3 ruling: an unknown roof may be shut, so printing under
    it risks printing a forecast for a closed park — the criterion's own
    prohibition. Withholding is correct under both resolutions."""
    park = _park(_venue("c", "Charlie Field", VenueType.RETRACTABLE_ROOF), roof=roof)
    assert forecast_disposition(park) is ForecastDisposition.WITHHELD_ROOF_UNDETERMINED
    text = forecast_text(park)
    assert "undetermined" in text
    assert str(_FORECAST.temperature_f) not in text


def test_an_open_roof_and_open_air_do_print_the_forecast() -> None:
    for venue_type in (VenueType.OPEN_AIR, VenueType.RETRACTABLE_ROOF):
        park = _park(_venue("d", "Delta Park", venue_type))
        assert forecast_disposition(park) is ForecastDisposition.APPLIES
        assert str(_FORECAST.temperature_f) in forecast_text(park)


def test_a_printed_forecast_says_where_the_wind_comes_from() -> None:
    """A bare compass pair reads as a target ("8 mph SW" looks like wind
    blowing toward the southwest). The source reports where wind blows
    *from*, and the screen says so in words."""
    park = _park(_venue("d", "Delta Park", VenueType.OPEN_AIR))
    assert f"from the {_FORECAST.wind_direction}" in forecast_text(park)


def test_the_disposition_is_total_over_every_constructible_park() -> None:
    """No default branch: every venue type crossed with every roof state the
    contract allows for it resolves to one of the three dispositions."""
    seen: set[ForecastDisposition] = set()
    for venue_type in VenueType:
        roofs: list[SnapshotField[RoofStatus]]
        if venue_type is VenueType.RETRACTABLE_ROOF:
            roofs = [SnapshotField.present(status, SOURCE_ID) for status in RoofStatus]
            roofs += [
                SnapshotField[RoofStatus].absent(reason, SOURCE_ID)
                for reason in (AbsenceReason.SOURCE_UNAVAILABLE, AbsenceReason.NOT_YET_OBSERVED)
            ]
        else:
            roofs = [SnapshotField[RoofStatus].absent(AbsenceReason.NOT_APPLICABLE)]
        for roof in roofs:
            seen.add(forecast_disposition(_park(_venue("e", "Echo Park", venue_type), roof=roof)))
    assert seen == set(ForecastDisposition)


# --- criterion 3: the adapter returning unavailable -------------------------


def test_the_screen_renders_when_the_forecast_is_unavailable() -> None:
    park = _park(
        _venue("f", "Foxtrot Park", VenueType.OPEN_AIR),
        forecast=SnapshotField[WeatherForecast].absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID),
    )
    text = forecast_text(park)
    assert "source unavailable" in text
    assert text.strip() != ""  # never a blank cell
    notes = unavailable_forecast_notes(_snapshot(park))
    assert len(notes) == 1
    assert "Foxtrot Park" in notes[0]


def test_a_suppressed_forecast_is_not_reported_as_an_unavailable_one() -> None:
    """The two are different facts: one is about the ballpark, the other about
    the source. A closed roof with no forecast is not an adapter failure."""
    park = _park(
        _venue("b", "Bravo Dome", VenueType.FIXED_ROOF),
        forecast=SnapshotField[WeatherForecast].absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID),
    )
    assert unavailable_forecast_notes(_snapshot(park)) == ()
    assert forecast_suppression_notes(_snapshot(park))


# --- criterion 2 and the no-ranking rule ------------------------------------


def test_rows_open_in_neutral_venue_name_order_never_factor_order() -> None:
    high = _park(_venue("z", "Zulu Park", VenueType.OPEN_AIR), lhb=_factor("150", Handedness.LEFT))
    low = _park(_venue("a", "Alpha Park", VenueType.OPEN_AIR), lhb=_factor("60", Handedness.LEFT))
    ordered = ordered_parks(_snapshot(high, low))
    assert [park.venue.name for park in ordered] == ["Alpha Park", "Zulu Park"]


def test_both_handedness_factors_sit_beside_venue_type_in_the_row() -> None:
    """Criterion 2 as a property of the rendered row, not only of the data."""
    frames = screen_frames(_snapshot(_park(_venue("a", "Alpha Park", VenueType.OPEN_AIR))))
    columns = list(frames.data.columns)
    assert columns[0] == VENUE_COLUMN
    assert columns.index(VENUE_TYPE_COLUMN) < columns.index(LHB_FACTOR_COLUMN)
    assert columns.index(LHB_FACTOR_COLUMN) < columns.index(RHB_FACTOR_COLUMN)
    assert set(ALL_COLUMNS) | {VENUE_COLUMN} == set(columns)
    assert frames.data.at[0, TEAM_COLUMN] == "Club Alpha"


def test_factor_columns_are_numeric_so_the_component_sorts_numerically() -> None:
    """The GMF-002 finding, inherited: a display-string column would sort
    lexicographically and put 90 above 110."""
    parks = (
        _park(_venue("a", "Alpha Park", VenueType.OPEN_AIR), lhb=_factor("110", Handedness.LEFT)),
        _park(_venue("b", "Bravo Park", VenueType.OPEN_AIR), lhb=_factor("90", Handedness.LEFT)),
    )
    frames = screen_frames(_snapshot(*parks))
    assert str(frames.data[LHB_FACTOR_COLUMN].dtype) == "float64"
    assert frames.data[LHB_FACTOR_COLUMN].tolist() == [110.0, 90.0]


def test_a_factor_cell_shows_its_sample_beside_the_value() -> None:
    frames = screen_frames(
        _snapshot(
            _park(
                _venue("a", "Alpha Park", VenueType.OPEN_AIR),
                lhb=_factor("110", Handedness.LEFT, sample=13560),
            )
        )
    )
    assert frames.texts.at[0, LHB_FACTOR_COLUMN] == "110 · PA 13560"


def test_condition_columns_carry_words_in_the_frame_itself() -> None:
    """Why the None-cell defect cannot reach them: their text is the frame's
    value, not a Styler display value the component may discard."""
    frames = screen_frames(_snapshot(_park(_venue("b", "Bravo Dome", VenueType.FIXED_ROOF))))
    assert isinstance(frames.data.at[0, ROOF_COLUMN], str)
    assert isinstance(frames.data.at[0, FORECAST_COLUMN], str)
    assert frames.data.at[0, ROOF_COLUMN] != ""


def test_an_absent_factor_is_missing_in_the_data_and_named_in_words() -> None:
    park = _park(
        _venue("a", "Alpha Park", VenueType.OPEN_AIR),
        lhb=_absent_factor(AbsenceReason.NOT_YET_OBSERVED),
    )
    frames = screen_frames(_snapshot(park))
    assert frames.data[LHB_FACTOR_COLUMN].isna().all()
    assert "not yet observed" in frames.texts.at[0, LHB_FACTOR_COLUMN]
    states = screen_state_frame(_snapshot(park))
    assert states.at[0, LHB_FACTOR_COLUMN] == DisplayState.NOT_YET_OBSERVED.value
    notes = factor_absence_notes(_snapshot(park))
    assert len(notes) == 1
    assert "Alpha Park" in notes[0]
    assert LHB_FACTOR_COLUMN in notes[0]
    assert "not yet observed" in notes[0]


def test_a_present_factor_produces_no_absence_note() -> None:
    assert factor_absence_notes(_snapshot(_park(_venue("a", "A", VenueType.OPEN_AIR)))) == ()


def test_the_three_absence_reasons_read_differently_on_a_factor() -> None:
    texts = set()
    for reason in AbsenceReason:
        park = _park(_venue("a", "Alpha Park", VenueType.OPEN_AIR), lhb=_absent_factor(reason))
        texts.add(screen_frames(_snapshot(park)).texts.at[0, LHB_FACTOR_COLUMN])
    assert len(texts) == 3


def test_factor_detail_notes_name_both_sides() -> None:
    notes = factor_detail_notes(_park(_venue("a", "Alpha Park", VenueType.OPEN_AIR)))
    assert len(notes) == len(FACTOR_COLUMNS)
    assert any(note.startswith(LHB_FACTOR_COLUMN) for note in notes)
    assert any(note.startswith(RHB_FACTOR_COLUMN) for note in notes)
