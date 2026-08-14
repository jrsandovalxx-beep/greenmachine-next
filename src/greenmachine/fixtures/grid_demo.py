"""The GMF-002 grid-demo snapshot — every display state, one screenful.

Five synthetic batters are chosen so the grid cannot render without showing
its whole vocabulary (the absence-versus-zero criterion has teeth):

- **Batter Alpha** — every metric present, with different values per named
  window, so switching windows visibly changes data.
- **Batter Bravo** — a **true zero over a positive sample**: a barrel rate of
  exactly zero across real batted-ball events. A present observation, never a
  blank, never an absence.
- **Batter Charlie** — every metric absent ``NOT_YET_OBSERVED``.
- **Batter Delta** — every metric absent ``SOURCE_UNAVAILABLE``.
- **Batter Echo** — every metric absent ``NOT_APPLICABLE``.

The exit-velocity column carries the **sort-divergence pair** (reviewer's
requirement): Alpha's ``1000.5`` against Bravo's ``950.5`` straddles a
digit-count boundary, so textual order ("1000.5…" before "950.5…") and
numeric order disagree — a lexicographic sort cannot pass by accident. The
fixture's job is to make defects visible.

Every value is a deliberately non-baseball validation artifact (OQ-4): shares
at extremes, four-digit "exit velocities", single-digit samples. The snapshot
is data for a screen, not a claim about baseball.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from greenmachine.inputs import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    BatterInputs,
    ExitVelocityAverage,
    InputSnapshot,
    SnapshotField,
    SourceKind,
    SourceRecord,
    SwingShare,
    Window,
    WindowedBatterMetrics,
    WindowedPitchTypeSplits,
)

CAPTURED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

SOURCE_ID = "grid-demo-synthetic"

_SOURCES = (
    SourceRecord(
        source_id=SOURCE_ID,
        kind=SourceKind.SYNTHETIC,
        description="grid-demo fixture values - deliberately non-baseball numbers (OQ-4)",
    ),
)

# Alpha's per-window spread: the same four metrics, different magnitudes, so a
# window switch is visible in every cell.
_ALPHA_RATES = {
    Window.RECENT_7D: (Decimal("0.900"), Decimal("1000.5"), Decimal("0.850"), Decimal("0.100")),
    Window.RECENT_14D: (Decimal("0.500"), Decimal("3.5"), Decimal("0.450"), Decimal("0.550")),
    Window.SEASON_TO_DATE: (Decimal("0.050"), Decimal("9.5"), Decimal("0.010"), Decimal("0.990")),
}


def _present_metrics(window: Window) -> WindowedBatterMetrics:
    barrel, mph, swing, air = _ALPHA_RATES[window]
    return WindowedBatterMetrics(
        window=window,
        barrel_rate=SnapshotField.present(
            BattedBallRate(rate=barrel, batted_ball_events=4), SOURCE_ID
        ),
        exit_velocity=SnapshotField.present(
            ExitVelocityAverage(miles_per_hour=mph, batted_ball_events=4), SOURCE_ID
        ),
        ideal_attack_angle_share=SnapshotField.present(
            SwingShare(share=swing, tracked_swings=5), SOURCE_ID
        ),
        pull_air_share=SnapshotField.present(AirBallShare(share=air, air_balls=3), SOURCE_ID),
    )


def _zero_metrics(window: Window) -> WindowedBatterMetrics:
    """The true zero: rate 0 over a positive denominator — a present value."""
    return WindowedBatterMetrics(
        window=window,
        barrel_rate=SnapshotField.present(
            BattedBallRate(rate=Decimal("0"), batted_ball_events=6), SOURCE_ID
        ),
        exit_velocity=SnapshotField.present(
            ExitVelocityAverage(miles_per_hour=Decimal("950.5"), batted_ball_events=6), SOURCE_ID
        ),
        ideal_attack_angle_share=SnapshotField.present(
            SwingShare(share=Decimal("0"), tracked_swings=7), SOURCE_ID
        ),
        pull_air_share=SnapshotField.present(
            AirBallShare(share=Decimal("0.500"), air_balls=2), SOURCE_ID
        ),
    )


def _absent_metrics(window: Window, reason: AbsenceReason) -> WindowedBatterMetrics:
    return WindowedBatterMetrics(
        window=window,
        barrel_rate=SnapshotField.absent(reason, SOURCE_ID),
        exit_velocity=SnapshotField.absent(reason, SOURCE_ID),
        ideal_attack_angle_share=SnapshotField.absent(reason, SOURCE_ID),
        pull_air_share=SnapshotField.absent(reason, SOURCE_ID),
    )


def _no_splits() -> tuple[WindowedPitchTypeSplits, ...]:
    """This snapshot feeds the GMF-002 batter grid, which renders no pitch-type
    split data at all. The splits are therefore absent rather than empty: an
    empty set would claim this batter was observed to face no tracked pitches,
    which is a measurement nobody took. ``NOT_YET_OBSERVED`` says the true
    thing — the fixture has not captured them."""
    return tuple(
        WindowedPitchTypeSplits(
            window=window,
            splits=SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID),
        )
        for window in Window
    )


def _batter(batter_id: str, name: str, windows: tuple[WindowedBatterMetrics, ...]) -> BatterInputs:
    return BatterInputs(
        batter_id=batter_id,
        name=name,
        windows=windows,
        pitch_type_splits=_no_splits(),
        plate_appearance_log=SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID),
    )


def _uniform(builder_reason: AbsenceReason) -> tuple[WindowedBatterMetrics, ...]:
    return tuple(_absent_metrics(window, builder_reason) for window in Window)


def grid_demo_snapshot() -> InputSnapshot:
    """The snapshot the GMF-002 grid renders — fixtures only, never a fetch."""
    return InputSnapshot(
        captured_at=CAPTURED_AT,
        sources=_SOURCES,
        batters=(
            _batter(
                "grid-demo-1",
                "Batter Alpha",
                tuple(_present_metrics(window) for window in Window),
            ),
            _batter(
                "grid-demo-2",
                "Batter Bravo",
                tuple(_zero_metrics(window) for window in Window),
            ),
            _batter("grid-demo-3", "Batter Charlie", _uniform(AbsenceReason.NOT_YET_OBSERVED)),
            _batter("grid-demo-4", "Batter Delta", _uniform(AbsenceReason.SOURCE_UNAVAILABLE)),
            _batter("grid-demo-5", "Batter Echo", _uniform(AbsenceReason.NOT_APPLICABLE)),
        ),
        parks=(),
    )
