"""GMF-001: contract invariants, absence semantics, and the park reference.

Criterion 2 (the contract), criterion 3 (thirty venues with venue type) and
the constructive halves of criteria 5 and 6.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from synthetic import (
    FIXED_VENUE,
    OPEN_AIR_VENUE,
    RETRACTABLE_VENUE,
    SOURCES,
    absent_metrics,
    make_batter,
    make_event,
    make_log,
    make_park,
    make_snapshot,
    present_metrics,
)

from greenmachine.inputs import (
    PARK_VENUES,
    AbsenceReason,
    BattedBallRate,
    DisplayState,
    ExitVelocityReading,
    Handedness,
    InputContractError,
    InputSnapshot,
    ManualExportProvenance,
    ParkFactor,
    ParkInputs,
    PlateAppearanceEvent,
    RoofStatus,
    SnapshotField,
    SourceAvailability,
    SourceKind,
    SourceRecord,
    VenueType,
    Window,
)

# ---------------------------------------------------------------------------
# SnapshotField: exactly one of value/absence, and a total display mapping
# ---------------------------------------------------------------------------


def test_a_field_with_neither_value_nor_absence_is_rejected() -> None:
    with pytest.raises(InputContractError):
        SnapshotField(value=None, absence=None, source_id=None)


def test_a_field_with_both_value_and_absence_is_rejected() -> None:
    with pytest.raises(InputContractError):
        SnapshotField(
            value=BattedBallRate(rate=Decimal("0"), batted_ball_events=0),
            absence=AbsenceReason.NOT_YET_OBSERVED,
            source_id="synthetic-fixture",
        )


def test_a_present_value_without_a_source_is_rejected() -> None:
    with pytest.raises(InputContractError):
        SnapshotField(
            value=BattedBallRate(rate=Decimal("0"), batted_ball_events=0),
            absence=None,
            source_id=None,
        )


def test_display_state_maps_every_absence_reason_distinctly() -> None:
    states = {reason: SnapshotField.absent(reason).display_state() for reason in AbsenceReason}
    assert states == {
        AbsenceReason.NOT_APPLICABLE: DisplayState.NOT_APPLICABLE,
        AbsenceReason.NOT_YET_OBSERVED: DisplayState.NOT_YET_OBSERVED,
        AbsenceReason.SOURCE_UNAVAILABLE: DisplayState.SOURCE_UNAVAILABLE,
    }
    assert len(set(states.values())) == 3


def test_a_present_field_displays_as_value() -> None:
    field = SnapshotField.present(
        BattedBallRate(rate=Decimal("0.5"), batted_ball_events=4), "synthetic-fixture"
    )
    assert field.display_state() is DisplayState.VALUE


# ---------------------------------------------------------------------------
# Value types: units, denominators, bounds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_rate", [Decimal("-0.01"), Decimal("1.01")])
def test_batted_ball_rate_bounds(bad_rate: Decimal) -> None:
    with pytest.raises(InputContractError):
        BattedBallRate(rate=bad_rate, batted_ball_events=1)


def test_batted_ball_rate_denominator_is_bbe_and_non_negative() -> None:
    with pytest.raises(InputContractError):
        BattedBallRate(rate=Decimal("0"), batted_ball_events=-1)
    assert "home runs included" in (BattedBallRate.__doc__ or "")


def test_provenance_validation() -> None:
    good = ManualExportProvenance(
        source_url="https://example.invalid/x",
        export_date=date(2026, 1, 1),
        row_count=1,
        sha256="0" * 64,
    )
    assert good.row_count == 1
    with pytest.raises(InputContractError):
        ManualExportProvenance("https://example.invalid/x", date(2026, 1, 1), 0, "0" * 64)
    with pytest.raises(InputContractError):
        ManualExportProvenance("https://example.invalid/x", date(2026, 1, 1), 1, "zz")


def test_a_manual_export_source_requires_provenance() -> None:
    with pytest.raises(InputContractError):
        SourceRecord(
            source_id="x",
            kind=SourceKind.MANUAL_EXPORT,
            description="missing provenance",
            availability=SourceAvailability.AVAILABLE,
        )


# ---------------------------------------------------------------------------
# Batter and park invariants
# ---------------------------------------------------------------------------


def test_duplicate_windows_are_rejected() -> None:
    with pytest.raises(InputContractError):
        make_batter(windows=(present_metrics(Window.RECENT_7D), present_metrics(Window.RECENT_7D)))


def test_metrics_for_returns_the_named_window_or_none() -> None:
    batter = make_batter(windows=(present_metrics(Window.RECENT_14D),))
    assert batter.metrics_for(Window.RECENT_14D) is not None
    assert batter.metrics_for(Window.SEASON_TO_DATE) is None


def test_park_factor_slot_handedness_is_enforced() -> None:
    with pytest.raises(InputContractError):
        ParkInputs(
            venue=OPEN_AIR_VENUE,
            park_factor_lhb=SnapshotField.present(
                ParkFactor(factor=Decimal("1"), handedness=Handedness.RIGHT, plate_appearances=3),
                "synthetic-fixture",
            ),
            park_factor_rhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            roof_status=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE),
            forecast=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
        )


def test_roof_status_is_not_applicable_outside_retractable_roofs() -> None:
    with pytest.raises(InputContractError):
        ParkInputs(
            venue=OPEN_AIR_VENUE,
            park_factor_lhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            park_factor_rhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            roof_status=SnapshotField.present(RoofStatus.OPEN, "synthetic-fixture"),
            forecast=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
        )


def test_a_retractable_roof_may_carry_an_explicit_unknown() -> None:
    park = make_park(venue=RETRACTABLE_VENUE)
    assert park.roof_status.value is RoofStatus.UNKNOWN


@pytest.mark.parametrize(
    ("venue_key", "reason"),
    [
        ("open", AbsenceReason.SOURCE_UNAVAILABLE),
        ("open", AbsenceReason.NOT_YET_OBSERVED),
        ("fixed", AbsenceReason.SOURCE_UNAVAILABLE),
    ],
)
def test_a_roof_that_does_not_exist_cannot_fail_or_be_pending(
    venue_key: str, reason: AbsenceReason
) -> None:
    """Finding 3: for open-air and fixed venues the only absence is NOT_APPLICABLE."""
    target = OPEN_AIR_VENUE if venue_key == "open" else FIXED_VENUE
    with pytest.raises(InputContractError):
        ParkInputs(
            venue=target,
            park_factor_lhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            park_factor_rhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            roof_status=SnapshotField.absent(reason),
            forecast=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
        )


def test_a_retractable_roof_state_is_never_not_applicable() -> None:
    """Finding 3, the other direction: the state is entirely applicable (D-055:
    an unknown roof is a PRESENT RoofStatus.UNKNOWN, not an absence)."""
    with pytest.raises(InputContractError):
        ParkInputs(
            venue=RETRACTABLE_VENUE,
            park_factor_lhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            park_factor_rhb=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            roof_status=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE),
            forecast=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
        )


# ---------------------------------------------------------------------------
# Snapshot invariants
# ---------------------------------------------------------------------------


def test_an_aware_non_utc_timestamp_is_rejected() -> None:
    """Finding 2: awareness alone is not the documented semantic; UTC is."""
    with pytest.raises(InputContractError):
        InputSnapshot(
            captured_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=5))),
            sources=SOURCES,
            batters=(),
            parks=(),
        )


def test_a_naive_timestamp_is_rejected() -> None:
    with pytest.raises(InputContractError):
        InputSnapshot(
            captured_at=datetime(2026, 1, 1, 12, 0, 0),
            sources=SOURCES,
            batters=(),
            parks=(),
        )


def test_an_unknown_source_id_is_rejected_at_snapshot_level() -> None:
    batter = make_batter(windows=(present_metrics(Window.RECENT_7D),))
    with pytest.raises(InputContractError):
        InputSnapshot(
            captured_at=make_snapshot().captured_at,
            sources=SOURCES[:1],  # drops the manual-export source the splits cite
            batters=(batter,),
            parks=(),
        )


def test_iter_fields_sweeps_every_observed_field() -> None:
    snapshot = make_snapshot()
    labels = [owner for owner, _ in snapshot.iter_fields()]
    # batter log (1) + one window (4) + one split (2) + three log events
    # (2 each) + one park (4)
    assert len(labels) == 17
    assert any("RECENT_7D" in label for label in labels)
    assert any("vs ZZ" in label for label in labels)
    assert any("event 0" in label for label in labels)
    assert any("venue synthetic-open" in label for label in labels)


def test_every_absence_reason_is_constructible_through_the_snapshot() -> None:
    for reason in AbsenceReason:
        snapshot = make_snapshot(
            batters=(make_batter(windows=(absent_metrics(Window.RECENT_7D, reason),)),),
        )
        batter_fields = [
            field for owner, field in snapshot.iter_fields() if owner.startswith("batter")
        ]
        window_fields = [f for f in batter_fields if f.absence is reason]
        assert len(window_fields) >= 4


# ---------------------------------------------------------------------------
# The batted-ball log: snapshot data, never a popup fetch
# ---------------------------------------------------------------------------


def test_unsorted_log_events_are_rejected() -> None:
    with pytest.raises(InputContractError):
        make_log(events=(make_event(date(2026, 1, 2)), make_event(date(2026, 1, 1))))


def test_a_present_empty_log_is_a_real_observation_distinct_from_absence() -> None:
    empty = SnapshotField.present(make_log(events=()), "synthetic-fixture")
    missing: SnapshotField[object] = SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE)
    assert empty.display_state() is DisplayState.VALUE
    assert empty.value is not None and empty.value.events == ()
    assert missing.display_state() is DisplayState.SOURCE_UNAVAILABLE


def test_a_non_contact_row_must_carry_not_applicable_measurements() -> None:
    with pytest.raises(InputContractError):
        PlateAppearanceEvent(
            event_date=date(2026, 1, 1),
            pitch_type="ZZ",
            result="synthetic_strikeout",
            batted_ball=False,
            exit_velocity=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            hit_distance=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE),
        )


def test_a_batted_ball_may_not_claim_not_applicable() -> None:
    with pytest.raises(InputContractError):
        PlateAppearanceEvent(
            event_date=date(2026, 1, 1),
            pitch_type="ZZ",
            result="synthetic_result",
            batted_ball=True,
            exit_velocity=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE),
            hit_distance=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
        )


def test_batted_ball_events_is_the_named_bbe_subpopulation() -> None:
    log = make_log()
    assert len(log.events) == 3
    bbe = log.batted_ball_events()
    assert len(bbe) == 2
    assert all(event.batted_ball for event in bbe)


def test_an_untracked_event_measurement_is_a_named_absence_never_a_null() -> None:
    event = make_event(tracked=False)
    assert event.exit_velocity.display_state() is DisplayState.SOURCE_UNAVAILABLE
    assert event.hit_distance.display_state() is DisplayState.SOURCE_UNAVAILABLE
    assert event.exit_velocity.value is None


def test_event_vocabulary_must_be_non_empty() -> None:
    with pytest.raises(InputContractError):
        PlateAppearanceEvent(
            event_date=date(2026, 1, 1),
            pitch_type="",
            result="synthetic_result",
            batted_ball=True,
            exit_velocity=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
            hit_distance=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
        )


def test_an_event_with_an_unknown_source_is_rejected_at_snapshot_level() -> None:
    event = PlateAppearanceEvent(
        event_date=date(2026, 1, 1),
        pitch_type="ZZ",
        result="synthetic_result",
        batted_ball=True,
        exit_velocity=SnapshotField.present(
            ExitVelocityReading(miles_per_hour=Decimal("1")), "no-such-source"
        ),
        hit_distance=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE),
    )
    batter = make_batter(log=SnapshotField.present(make_log(events=(event,)), "synthetic-fixture"))
    with pytest.raises(InputContractError):
        make_snapshot(batters=(batter,))


# ---------------------------------------------------------------------------
# Criterion 3: the park reference — thirty venues, venue type per D-055
# ---------------------------------------------------------------------------


def test_park_reference_holds_exactly_thirty_venues() -> None:
    assert len(PARK_VENUES) == 30


def test_park_reference_ids_names_and_teams_are_unique() -> None:
    for attribute in ("venue_id", "name", "team"):
        values = [getattr(venue, attribute) for venue in PARK_VENUES]
        assert len(values) == len(set(values)), f"duplicate {attribute}"


def test_park_reference_partition_by_venue_type() -> None:
    counts = Counter(venue.venue_type for venue in PARK_VENUES)
    assert counts == {
        VenueType.OPEN_AIR: 22,
        VenueType.RETRACTABLE_ROOF: 7,
        VenueType.FIXED_ROOF: 1,
    }


def test_every_park_reference_row_is_a_valid_venue() -> None:
    for venue in PARK_VENUES:
        assert venue.venue_id and venue.name and venue.team
        assert isinstance(venue.venue_type, VenueType)


def test_savant_join_ids_are_unique_and_absent_only_for_the_athletics() -> None:
    joined = [v for v in PARK_VENUES if v.savant_venue_id is not None]
    missing = [v for v in PARK_VENUES if v.savant_venue_id is None]
    assert len(joined) == 29
    ids = [v.savant_venue_id for v in joined]
    assert len(ids) == len(set(ids))
    assert [v.team for v in missing] == ["Athletics"]  # the gap is represented, never filled
