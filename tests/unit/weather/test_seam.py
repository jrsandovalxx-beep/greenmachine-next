"""GMF-004 criterion 3: the weather seam, and criterion 5's prohibitions.

The seam's value is that it is *only* a seam. These tests assert what the
module does not contain as firmly as what it does: no provider, no URL, no
credential, no network client — because the cheapest moment to bind one by
accident is the moment the interface appears.
"""

from __future__ import annotations

from pathlib import Path

from greenmachine.fixtures import CONDITIONS_SOURCE_ID, FixtureWeatherAdapter, parks_demo_snapshot
from greenmachine.inputs import (
    PARK_VENUES,
    AbsenceReason,
    DisplayState,
    ParkVenue,
    RoofStatus,
    VenueType,
)
from greenmachine.weather import WeatherAdapter

SRC = Path(__file__).resolve().parents[3] / "src" / "greenmachine"


def test_the_fixture_adapter_satisfies_the_seam() -> None:
    """Structural conformance, checked rather than declared: the fixture does
    not inherit the protocol, so this is the only thing keeping it honest."""
    adapter: WeatherAdapter = FixtureWeatherAdapter()
    venue = PARK_VENUES[0]
    field = adapter.forecast_for(venue)
    assert field.display_state() in set(DisplayState)


def test_unavailability_is_a_return_value_not_an_exception() -> None:
    """Criterion 3's named case: the screen renders correctly with the adapter
    returning unavailable, which requires the adapter to *return*."""
    adapter = FixtureWeatherAdapter()
    rogers = next(v for v in PARK_VENUES if v.venue_id == "rogers-centre")
    field = adapter.forecast_for(rogers)
    assert field.value is None
    assert field.absence is AbsenceReason.SOURCE_UNAVAILABLE
    assert field.source_id == CONDITIONS_SOURCE_ID


def test_the_fixture_cannot_silently_invent_coverage() -> None:
    """A venue neither table names comes back ``NOT_YET_OBSERVED``, never
    valued: a fixture that answered for anything unnamed would claim coverage
    it lacks. The ratified adapter behaviour, asserted rather than described —
    this test's first version asserted a tautology and proved nothing.
    """
    adapter = FixtureWeatherAdapter()
    unknown = ParkVenue("nowhere-park", "Nowhere Park", "Club Zulu", VenueType.OPEN_AIR, None)
    field = adapter.forecast_for(unknown)
    assert field.value is None
    assert field.absence is AbsenceReason.NOT_YET_OBSERVED
    assert field.source_id == CONDITIONS_SOURCE_ID
    # The contrast that proves the tables drive the answer: a named-present
    # venue answers with a value, and a named-absent one with its own reason.
    truist = next(v for v in PARK_VENUES if v.venue_id == "truist-park")
    assert adapter.forecast_for(truist).value is not None
    fenway = next(v for v in PARK_VENUES if v.venue_id == "fenway-park")
    assert adapter.forecast_for(fenway).absence is AbsenceReason.NOT_YET_OBSERVED


def test_the_fixture_tables_name_only_real_venues_and_cover_them_all() -> None:
    """Every id in the fixture's tables is a reference venue, the present and
    absent tables are disjoint, and together they cover exactly the thirty —
    so the composed page exercises no default and a slug typo cannot silently
    turn a named venue into an unnamed one."""
    from greenmachine.fixtures.parks_demo import _FORECAST_ABSENT, _FORECAST_PRESENT

    reference = {venue.venue_id for venue in PARK_VENUES}
    named_absent = set(_FORECAST_ABSENT)
    named_present = set(_FORECAST_PRESENT)
    assert named_absent <= reference
    assert named_present <= reference
    assert not (named_absent & named_present)
    assert named_absent | named_present == reference


def test_the_seam_module_contains_no_provider_and_no_client() -> None:
    text = (SRC / "weather" / "adapter.py").read_text(encoding="utf-8")
    for banned in ("requests", "urllib", "httpx", "aiohttp", "socket", "api_key", "token"):
        assert banned not in text, f"{banned!r} appears in the weather seam"


def test_no_ballpark_pal_or_seamheads_anywhere_in_the_tree() -> None:
    """Criterion 5 and D-057 boundary 2, as a whole-source sweep rather than an
    attestation: excluded sources are excluded by absence, not by promise."""
    hits: list[str] = []
    for path in SRC.rglob("*.py"):
        lowered = path.read_text(encoding="utf-8").lower()
        for banned in ("ballpark pal", "ballparkpal", "seamheads"):
            if banned in lowered:
                hits.append(f"{path.name}: {banned}")
    assert hits == []


def test_roof_states_bind_from_the_fixture_and_obey_the_contract() -> None:
    """All three D-055 states plus an unobtained one reach the screen, and no
    non-retractable venue carries a roof state the contract forbids."""
    snapshot = parks_demo_snapshot()
    present = {
        park.roof_status.value
        for park in snapshot.parks
        if park.venue.venue_type is VenueType.RETRACTABLE_ROOF and park.roof_status.value
    }
    assert present == set(RoofStatus)
    unobtained = [
        park
        for park in snapshot.parks
        if park.venue.venue_type is VenueType.RETRACTABLE_ROOF and park.roof_status.value is None
    ]
    assert unobtained, "no venue exercises the unobtained-roof path"
    for park in snapshot.parks:
        if park.venue.venue_type is not VenueType.RETRACTABLE_ROOF:
            assert park.roof_status.absence is AbsenceReason.NOT_APPLICABLE


def test_the_composed_snapshot_keeps_its_two_provenances_separable() -> None:
    """Real pinned factors and fixture conditions never merge into one source:
    a reader can tell which is which from the snapshot alone."""
    snapshot = parks_demo_snapshot()
    kinds = {source.source_id: source.kind.value for source in snapshot.sources}
    assert kinds["savant-park-factors"] == "manual_export"
    assert kinds[CONDITIONS_SOURCE_ID] == "synthetic"
    assert len(snapshot.parks) == len(PARK_VENUES) == 30
    for park in snapshot.parks:
        assert park.forecast.source_id == CONDITIONS_SOURCE_ID
        for field in (park.park_factor_lhb, park.park_factor_rhb):
            assert field.source_id == "savant-park-factors"
