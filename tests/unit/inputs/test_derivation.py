"""The sourced-versus-derived boundary, guarded where the field sweep cannot.

``test_field_discipline.py`` deliberately excludes ``SnapshotField`` from its
sweep as the absence machinery, so ``SnapshotField.derivation`` gets no
protection from that module. This one supplies it, and the strongest guard is
not here at all: ``InputSnapshot.__post_init__`` rejects a derivation whose
named inputs do not resolve to fields of the same snapshot, which makes
"auditable" an invariant rather than a claim a string makes.

Nothing in §GMF-003 derives anything. These tests prove the representation is
honest **before** a derived value exists, because the moment one does — the
banked AB-K rule at §GMF-006 — the machinery has to already be trustworthy.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from synthetic import (
    SOURCE_EXPORT,
    make_batter,
    make_snapshot,
    present_split,
    windowed_splits,
)

from greenmachine.inputs import (
    AbsenceReason,
    Derivation,
    DisplayState,
    InputContractError,
    InputSnapshot,
    SnapshotField,
    UsageShare,
    Window,
)

USAGE_LABEL = "batter synthetic-batter-1 SEASON_TO_DATE vs QQ.usage_share"


def _usage(share: str = "0.5") -> UsageShare:
    return UsageShare(share=Decimal(share), sample_pitches=4)


def test_a_sourced_value_carries_no_derivation() -> None:
    """``present`` is the sourced constructor and cannot make the other claim."""
    field = SnapshotField.present(_usage(), SOURCE_EXPORT)
    assert field.derivation is None
    assert field.display_state() is DisplayState.VALUE


def test_a_derived_value_carries_its_formula_and_inputs() -> None:
    field = SnapshotField.derived(
        _usage(),
        formula="swinging strikes / pitches",
        inputs=(USAGE_LABEL,),
        source_id=SOURCE_EXPORT,
    )
    assert field.derivation is not None
    assert field.derivation.formula == "swinging strikes / pitches"
    assert field.derivation.inputs == (USAGE_LABEL,)


def test_every_existing_field_in_a_snapshot_reads_as_sourced() -> None:
    """The regression that matters most: adding the slot must not have made
    anything already in the contract start claiming to be derived."""
    snapshot = make_snapshot()
    derived = [owner for owner, field in snapshot.iter_fields() if field.derivation is not None]
    assert derived == []


def test_a_derivation_must_state_a_formula() -> None:
    with pytest.raises(InputContractError):
        Derivation(formula="   ", inputs=("a",))


def test_a_derivation_must_name_at_least_one_input() -> None:
    """A value derived from nothing is a sourced value or an invention."""
    with pytest.raises(InputContractError):
        Derivation(formula="x / y", inputs=())


def test_a_derivation_input_label_must_be_non_empty() -> None:
    with pytest.raises(InputContractError):
        Derivation(formula="x / y", inputs=("",))


def _snapshot_with_derived_usage(inputs: tuple[str, ...]) -> InputSnapshot:
    """A snapshot whose one split carries a derived usage share naming ``inputs``.

    Deliberately a derivation nobody would want — usage is sourced in reality —
    because the point under test is the audit machinery, not the arithmetic.
    """
    derived = SnapshotField.derived(
        _usage(), formula="pitches of type / sample pitches", inputs=inputs, source_id=SOURCE_EXPORT
    )
    split = replace(present_split(pitch_type="QQ"), usage_share=derived)
    batter = make_batter(splits=(windowed_splits(Window.SEASON_TO_DATE, (split,)),))
    return make_snapshot(batters=(batter,))


def test_a_derivation_whose_inputs_resolve_is_accepted() -> None:
    snapshot = _snapshot_with_derived_usage(
        ("batter synthetic-batter-1 SEASON_TO_DATE vs QQ.whiff_rate",)
    )
    derived = [owner for owner, field in snapshot.iter_fields() if field.derivation is not None]
    assert derived == [USAGE_LABEL]


def test_a_derivation_naming_a_field_that_does_not_exist_is_rejected() -> None:
    """This is what makes the audit trail checkable rather than decorative: a
    plausible-looking label that names nothing fails at construction."""
    with pytest.raises(InputContractError):
        _snapshot_with_derived_usage(("batter synthetic-batter-1 SEASON_TO_DATE vs QQ.put_away",))


def test_a_derivation_may_not_name_itself_as_an_input() -> None:
    with pytest.raises(InputContractError):
        _snapshot_with_derived_usage((USAGE_LABEL,))


def test_a_derived_value_may_be_absent_and_keep_its_derivation() -> None:
    """A derivation propagates its inputs' absence with the reason intact, and
    the derivation survives to say which computation could not be completed."""
    field: SnapshotField[UsageShare] = SnapshotField.absent(
        AbsenceReason.SOURCE_UNAVAILABLE,
        SOURCE_EXPORT,
        derivation=Derivation(formula="x / y", inputs=(USAGE_LABEL,)),
    )
    assert field.display_state() is DisplayState.SOURCE_UNAVAILABLE
    assert field.derivation is not None
