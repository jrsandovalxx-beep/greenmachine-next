"""GMF-001 criterion 6, property form: absence always renders a defined state.

Hypothesis drives arbitrary absence assignments through every observed field of
a snapshot and asserts two properties the contract exists to guarantee:

1. every field renders a defined ``DisplayState`` — total, never ``None``,
   never an exception;
2. no field silently defaults — an absent field exposes no value, and the
   assigned reason survives round-trip to the rendered state, distinctly per
   reason.

The Hypothesis seed is the repository-fixed ``--hypothesis-seed=20260724``
(ADR-0008) carried by ``addopts``.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st
from synthetic import absent_metrics, make_batter, make_park, make_snapshot

from greenmachine.inputs import (
    AbsenceReason,
    BattedBallRate,
    DisplayState,
    SnapshotField,
    Window,
)

_REASONS = st.sampled_from(sorted(AbsenceReason, key=lambda r: r.value))
_WINDOWS = st.sampled_from(sorted(Window, key=lambda w: w.value))

_EXPECTED_STATE = {
    AbsenceReason.NOT_APPLICABLE: DisplayState.NOT_APPLICABLE,
    AbsenceReason.NOT_YET_OBSERVED: DisplayState.NOT_YET_OBSERVED,
    AbsenceReason.SOURCE_UNAVAILABLE: DisplayState.SOURCE_UNAVAILABLE,
}


@given(reason=_REASONS)
def test_an_absent_field_renders_its_exact_reason(reason: AbsenceReason) -> None:
    field: SnapshotField[BattedBallRate] = SnapshotField.absent(reason)
    state = field.display_state()
    assert isinstance(state, DisplayState)
    assert state == _EXPECTED_STATE[reason]
    assert field.value is None  # no silent default


@given(reason=_REASONS, window=_WINDOWS)
def test_every_field_of_an_absent_window_is_defined_and_valueless(
    reason: AbsenceReason, window: Window
) -> None:
    snapshot = make_snapshot(batters=(make_batter(windows=(absent_metrics(window, reason),)),))
    for owner, field in snapshot.iter_fields():
        state = field.display_state()
        assert isinstance(state, DisplayState), owner
        if field.absence is reason and owner.startswith("batter"):
            assert state == _EXPECTED_STATE[reason], owner
            assert field.value is None, owner


@given(
    factor_reason=st.one_of(st.none(), _REASONS),
    forecast_reason=st.one_of(st.none(), _REASONS),
)
def test_park_fields_render_defined_states_under_any_absence_mix(
    factor_reason: AbsenceReason | None, forecast_reason: AbsenceReason | None
) -> None:
    park = make_park(factor_reason=factor_reason, forecast_reason=forecast_reason)
    snapshot = make_snapshot(parks=(park,))
    states = {owner: field.display_state() for owner, field in snapshot.iter_fields()}
    assert all(isinstance(state, DisplayState) for state in states.values())
    forecast_state = states["venue synthetic-open.forecast"]
    if forecast_reason is None:
        assert forecast_state is DisplayState.VALUE
    else:
        assert forecast_state == _EXPECTED_STATE[forecast_reason]


@given(
    rate=st.decimals(min_value=Decimal("0"), max_value=Decimal("1"), places=3),
    bbe=st.integers(min_value=0, max_value=999),
)
def test_a_present_rate_always_carries_its_denominator_beside_it(rate: Decimal, bbe: int) -> None:
    value = BattedBallRate(rate=rate, batted_ball_events=bbe)
    field = SnapshotField.present(value, "synthetic-fixture")
    assert field.display_state() is DisplayState.VALUE
    assert field.value is not None
    assert field.value.batted_ball_events == bbe  # D-014: confidence beside, never fused


@given(
    contact=st.integers(min_value=0, max_value=9), non_contact=st.integers(min_value=0, max_value=9)
)
def test_contact_rates_divide_by_bbe_never_by_plate_appearances(
    contact: int, non_contact: int
) -> None:
    """The BABIP error in new clothes, guarded: a batter with strikeouts and
    walks in the window yields the same contact rate as that batter's batted
    balls alone, because the named denominator is the BBE subpopulation."""
    from datetime import date

    from synthetic import make_event, make_log, make_non_contact_event

    events = tuple(make_event(date(2026, 1, 1)) for _ in range(contact)) + tuple(
        make_non_contact_event(date(2026, 1, 2)) for _ in range(non_contact)
    )
    log = make_log(events=events)
    bbe = log.batted_ball_events()
    assert len(bbe) == contact
    assert len(log.events) == contact + non_contact
    tracked_hard = [e for e in bbe if e.exit_velocity.value is not None]
    if contact:
        rate_over_bbe = Decimal(len(tracked_hard)) / Decimal(len(bbe))
        contact_only_log = make_log(
            events=tuple(make_event(date(2026, 1, 1)) for _ in range(contact))
        )
        rate_contact_only = Decimal(
            len(
                [
                    e
                    for e in contact_only_log.batted_ball_events()
                    if e.exit_velocity.value is not None
                ]
            )
        ) / Decimal(len(contact_only_log.batted_ball_events()))
        assert rate_over_bbe == rate_contact_only  # strikeouts and walks moved nothing
    if non_contact:
        assert len(log.events) != len(bbe)  # dividing by len(events) is the reachable trap
