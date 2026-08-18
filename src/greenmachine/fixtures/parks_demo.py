"""The §GMF-004 parks snapshot: pinned factors, fixture conditions (criterion 6).

Two sources, deliberately separable, because they have genuinely different
standing:

- **Park factors** are the real pinned Savant export GMF-001 committed — the
  Product Owner's manual download of 2026-08-06, digest-verified on every read
  (D-053/D-057). Criterion 2 asks the screen to render *pinned* factors, so it
  renders those and not a synthetic stand-in.
- **Roof state and weather** have no source in this ticket. They come from the
  fixture below, and the screen says so: the seam exists (criterion 3), it is
  bound to a fixture here, and §GMF-005 is where a live NWS adapter arrives.

Fixture condition values are deliberately non-baseball (OQ-4): an 88.8 mph wind
at 111.1 °F is a validation artifact, not a forecast, so no reader of the
public page can mistake the conditions columns for real data (D-051/D-052).

The fixture covers every state the screen can render, because a fixture that
only exercises the happy path proves the happy path:

- all three venue types, and all three D-055 roof states on retractables;
- a retractable whose roof state is **absent**, exercising the withheld path;
- a forecast that is **source unavailable** where the roof does not suppress
  it (criterion 3's named case — Rogers Centre, which NWS does not cover);
- a forecast **not yet observed** at an open-air park, distinct from the above;
- the Athletics' **absent park factors**, the gap provenance finding one records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from greenmachine.inputs import (
    PARK_VENUES,
    AbsenceReason,
    Handedness,
    InputSnapshot,
    ParkInputs,
    ParkVenue,
    RoofStatus,
    SnapshotField,
    SourceKind,
    SourceRecord,
    VenueType,
    WeatherForecast,
)
from greenmachine.inputs.savant_park_factors import SOURCE as SAVANT_SOURCE
from greenmachine.inputs.savant_park_factors import factor_fields, read_factors

CAPTURED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

CONDITIONS_SOURCE_ID = "parks-demo-conditions"

CONDITIONS_SOURCE = SourceRecord(
    source_id=CONDITIONS_SOURCE_ID,
    kind=SourceKind.SYNTHETIC,
    description=(
        "parks-demo fixture conditions - roof state and weather bound to a fixture "
        "for GMF-004 (OQ-4 non-baseball values); the live NWS adapter arrives at GMF-005"
    ),
)

# Roof state per retractable venue. Every retractable venue in the reference
# data is named: an unnamed one falls through to NOT_YET_OBSERVED below rather
# than being quietly assumed open, which would be the fixture inventing a fact.
_ROOF_FIXTURE: dict[str, RoofStatus] = {
    "chase-field": RoofStatus.OPEN,
    "daikin-park": RoofStatus.CLOSED,
    "loandepot-park": RoofStatus.UNKNOWN,
    "american-family-field": RoofStatus.OPEN,
    "t-mobile-park": RoofStatus.CLOSED,
    "rogers-centre": RoofStatus.OPEN,
}

# Globe Life Field is deliberately absent from the table above: its roof state
# is unobtained, which is a different thing from unknown-at-game-time, and the
# screen must withhold its forecast for that reason too.
_ROOF_ABSENT: dict[str, AbsenceReason] = {
    "globe-life-field": AbsenceReason.SOURCE_UNAVAILABLE,
}

_SYNTHETIC_FORECAST = WeatherForecast(
    temperature_f=Decimal("111.1"),
    wind_speed_mph=Decimal("88.8"),
    wind_direction="NNE",
    short_forecast="Synthetic fixture conditions (OQ-4)",
)

# Venues whose forecast is deliberately absent, with the reason each names.
# Rogers Centre is the honest case D-055 itself calls out: NWS covers the US
# only, so a Toronto forecast is a source that cannot answer, not one that
# failed. Fenway carries the other absence so the two read differently on
# screen.
_FORECAST_ABSENT: dict[str, AbsenceReason] = {
    "rogers-centre": AbsenceReason.SOURCE_UNAVAILABLE,
    "fenway-park": AbsenceReason.NOT_YET_OBSERVED,
}

# Venues the fixture answers for, each named deliberately: the remaining 28 of
# the thirty reference venues. The adapter's default for a venue in NEITHER
# table is a NOT_YET_OBSERVED absence, never a value — a fixture that answered
# for anything unnamed would be claiming coverage it does not have, and the
# seam exists precisely so missing coverage is a visible state (the ratified
# adapter behaviour, asserted by test).
_FORECAST_PRESENT: frozenset[str] = frozenset(
    {
        "chase-field",
        "sutter-health-park",
        "truist-park",
        "camden-yards",
        "wrigley-field",
        "rate-field",
        "great-american-ball-park",
        "progressive-field",
        "coors-field",
        "comerica-park",
        "daikin-park",
        "kauffman-stadium",
        "angel-stadium",
        "dodger-stadium",
        "loandepot-park",
        "american-family-field",
        "target-field",
        "citi-field",
        "yankee-stadium",
        "citizens-bank-park",
        "pnc-park",
        "petco-park",
        "t-mobile-park",
        "oracle-park",
        "busch-stadium",
        "tropicana-field",
        "globe-life-field",
        "nationals-park",
    }
)


@dataclass(frozen=True)
class FixtureWeatherAdapter:
    """The `WeatherAdapter` binding for §GMF-004: two tables, and nothing live.

    Structurally a ``greenmachine.weather.WeatherAdapter``; the protocol is not
    imported here so the fixture package stays free of the seam's import, and
    the conformance is asserted by test rather than by inheritance.

    A venue neither table names returns ``NOT_YET_OBSERVED`` rather than a
    value: a fixture that answered for anything unnamed would be claiming
    coverage it does not have, and the whole point of the seam is that missing
    coverage is a visible state. Every answer this adapter gives — present or
    absent — is a row in a table above, so its coverage is auditable by
    reading, and its default is an absence.
    """

    def forecast_for(self, venue: ParkVenue) -> SnapshotField[WeatherForecast]:
        reason = _FORECAST_ABSENT.get(venue.venue_id)
        if reason is not None:
            return SnapshotField[WeatherForecast].absent(reason, CONDITIONS_SOURCE_ID)
        if venue.venue_id in _FORECAST_PRESENT:
            return SnapshotField.present(_SYNTHETIC_FORECAST, CONDITIONS_SOURCE_ID)
        return SnapshotField[WeatherForecast].absent(
            AbsenceReason.NOT_YET_OBSERVED, CONDITIONS_SOURCE_ID
        )


def _roof_field(venue: ParkVenue) -> SnapshotField[RoofStatus]:
    """The roof field, obeying the contract's two-directional D-055 rule.

    A venue without a retractable roof has no roof *state* to observe, so its
    only lawful absence is NOT_APPLICABLE — the contract rejects any other, and
    this fixture does not try to supply one.
    """
    if venue.venue_type is not VenueType.RETRACTABLE_ROOF:
        return SnapshotField[RoofStatus].absent(AbsenceReason.NOT_APPLICABLE)
    status = _ROOF_FIXTURE.get(venue.venue_id)
    if status is not None:
        return SnapshotField.present(status, CONDITIONS_SOURCE_ID)
    reason = _ROOF_ABSENT.get(venue.venue_id, AbsenceReason.NOT_YET_OBSERVED)
    return SnapshotField[RoofStatus].absent(reason, CONDITIONS_SOURCE_ID)


def parks_demo_snapshot(adapter: FixtureWeatherAdapter | None = None) -> InputSnapshot:
    """All thirty venues: pinned factors, fixture roof and weather.

    The adapter is a parameter so a test can bind a different one without
    touching the screen — which is the seam doing its job at the only scale
    this ticket has.
    """
    weather = adapter if adapter is not None else FixtureWeatherAdapter()
    factors = read_factors()
    parks = tuple(
        ParkInputs(
            venue=venue,
            park_factor_lhb=factor_fields(venue, factors)[Handedness.LEFT],
            park_factor_rhb=factor_fields(venue, factors)[Handedness.RIGHT],
            roof_status=_roof_field(venue),
            forecast=weather.forecast_for(venue),
        )
        for venue in PARK_VENUES
    )
    return InputSnapshot(
        captured_at=CAPTURED_AT,
        sources=(SAVANT_SOURCE, CONDITIONS_SOURCE),
        batters=(),
        parks=parks,
    )
