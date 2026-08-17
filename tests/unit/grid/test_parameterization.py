"""Old-path preservation, proved at the function boundary.

The GMF-002 grid's builders gained a column set and a row source so §GMF-003
could render pitch types through the same mechanism. The existing suite passing
proves *behaviour* is intact; it does not prove that the defaulted path is the
same path. The reviewer asked for the stronger claim, so these tests assert that
calling each parameterized function with no column argument equals calling it
with ``METRIC_COLUMNS`` explicitly, and that the four original value types still
render exactly as they did.

Nothing here changes what an absent GMF-002 cell displays. That would cross the
GMF-002 boundary, and the absence texts asserted below are the same three
strings the approved head shipped.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from greenmachine.fixtures import grid_demo_snapshot
from greenmachine.grid import BATTER_COLUMN, METRIC_COLUMNS, visible_columns
from greenmachine.grid.view import (
    _green,
    cell_text,
    graded_styler,
    grid_frame,
    style_frame,
)
from greenmachine.inputs import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    ExitVelocityAverage,
    SnapshotField,
    SwingShare,
    Window,
)

SNAPSHOT = grid_demo_snapshot()
SOURCE = "grid-demo-synthetic"


def _frames() -> tuple[object, object, object]:
    from greenmachine.grid import display_texts

    window = Window.SEASON_TO_DATE
    return (
        grid_frame(SNAPSHOT, window),
        display_texts(SNAPSHOT, window),
        style_frame(SNAPSHOT, window),
    )


def test_graded_styler_default_columns_are_the_batter_grid_columns() -> None:
    """The default *is* the old set, not merely a set that behaves like it."""
    data, texts, styles = _frames()
    # The uuid is per-Styler-instance and salts every generated CSS id, so it is
    # pinned to the same value on both sides: the comparison is of rendered
    # content, not of object identity.
    defaulted = graded_styler(data, texts, styles).set_uuid("fixed").to_html()  # type: ignore[arg-type]
    explicit = (
        graded_styler(data, texts, styles, METRIC_COLUMNS).set_uuid("fixed").to_html()  # type: ignore[arg-type]
    )
    assert defaulted == explicit
    # The comparison must be able to fail: a different column set renders
    # differently, so equality above is evidence rather than a tautology.
    narrowed = (
        graded_styler(data, texts, styles, ("Barrel rate",)).set_uuid("fixed").to_html()  # type: ignore[arg-type]
    )
    assert narrowed != defaulted


def test_visible_columns_defaults_are_the_batter_grids_identity_and_metrics() -> None:
    for chosen in [
        METRIC_COLUMNS,
        ("Barrel rate",),
        ("Pull air", "Barrel rate"),
        (),
    ]:
        assert visible_columns(chosen) == visible_columns(chosen, BATTER_COLUMN, METRIC_COLUMNS)


def test_visible_columns_still_leads_with_identity_in_canonical_order() -> None:
    """The behaviour the default encodes, pinned independently of the default."""
    assert visible_columns(("Pull air", "Barrel rate")) == [
        BATTER_COLUMN,
        "Barrel rate",
        "Pull air",
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (BattedBallRate(rate=Decimal("0.250"), batted_ball_events=4), "0.250 · BBE 4"),
        (
            ExitVelocityAverage(miles_per_hour=Decimal("950.5"), batted_ball_events=6),
            "950.5 mph · BBE 6",
        ),
        (SwingShare(share=Decimal("0.001"), tracked_swings=2), "0.001 · swings 2"),
        (AirBallShare(share=Decimal("1"), air_balls=3), "1 · air balls 3"),
    ],
)
def test_the_four_original_value_types_render_exactly_as_before(
    value: object, expected: str
) -> None:
    """The dispatch grew four branches; these four did not move."""
    assert cell_text(SnapshotField.present(value, SOURCE)) == expected


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (AbsenceReason.NOT_APPLICABLE, "not applicable"),
        (AbsenceReason.NOT_YET_OBSERVED, "not yet observed"),
        (AbsenceReason.SOURCE_UNAVAILABLE, "source unavailable"),
    ],
)
def test_absent_cell_text_is_unchanged(reason: AbsenceReason, expected: str) -> None:
    """The GMF-002 boundary, asserted rather than promised: what an absent cell
    displays is exactly what the approved head displayed."""
    field: SnapshotField[object] = SnapshotField.absent(reason, SOURCE)
    assert cell_text(field) == expected


def test_an_unrecognised_value_type_raises_instead_of_borrowing_a_format() -> None:
    """The old dispatch fell through to AirBallShare's format. On a surface whose
    denominators are near-identical, a wrong-but-plausible cell is worse than a
    crash — so the dispatch is total."""

    class Impostor:
        share = Decimal("0.5")
        air_balls = 3

    with pytest.raises(TypeError):
        cell_text(SnapshotField.present(Impostor(), SOURCE))


def test_the_green_scale_is_untouched() -> None:
    """The grading function itself moved not at all."""
    assert _green(0.0) == "color: #0a3622; background-color: rgb(233, 247, 233)"
    assert _green(1.0) == "color: #0a3622; background-color: rgb(111, 183, 121)"
