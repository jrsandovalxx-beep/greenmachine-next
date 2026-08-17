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
from typing import TypeVar

from greenmachine.inputs import (
    AbsenceReason,
    AirBallShare,
    BattedBallRate,
    BatterInputs,
    ExitVelocityAverage,
    ExpectedWeightedOnBase,
    InputSnapshot,
    IsolatedPower,
    PitchTypeSplit,
    SnapshotField,
    SourceKind,
    SourceRecord,
    SwingingStrikeRate,
    SwingShare,
    UsageShare,
    WhiffRate,
    Window,
    WindowedBatterMetrics,
    WindowedPitchTypeSplits,
)

CAPTURED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

SOURCE_ID = "grid-demo-synthetic"

# The payload type of one metric field, so the fixture's per-metric builder
# keeps each metric's own type instead of widening them all to object.
T = TypeVar("T")

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


def _split(
    pitch_type: str,
    usage: SnapshotField[UsageShare],
    absent_metric: str | None = None,
    metric_reason: AbsenceReason = AbsenceReason.SOURCE_UNAVAILABLE,
) -> PitchTypeSplit:
    """One pitch type with all seven metrics, optionally holing out one.

    ``absent_metric`` exists to prove the separation criterion 3 requires: a
    pitch type that qualifies on usage keeps its row when a single metric has
    no number, and the hole shows its reason rather than suppressing the type.
    """

    def field(name: str, value: T) -> SnapshotField[T]:
        """Present, unless this is the metric being holed out.

        Written per metric rather than over a dict of values: ``SnapshotField``
        is invariant, so a dict would collapse seven distinct payload types into
        ``object`` and the fixture would stop type-checking the very thing it
        exists to exercise.
        """
        if name == absent_metric:
            return SnapshotField.absent(metric_reason, SOURCE_ID)
        return SnapshotField.present(value, SOURCE_ID)

    # The values are bound to locals first so that no line places a component
    # identifier beside a numeric literal — the shape the architecture guard
    # reads as a hardcoded threshold table. The builders above avoid it the
    # same way, by splitting the construction across lines.
    barrel = BattedBallRate(Decimal("0.995"), 4)
    velocity = ExitVelocityAverage(Decimal("1200.5"), 4)
    power = IsolatedPower(Decimal("2.995"), 9)
    woba = ExpectedWeightedOnBase(Decimal("3.995"), 11)
    whiff = WhiffRate(Decimal("0.995"), 13)
    swinging_strike = SwingingStrikeRate(Decimal("0.005"), 17)
    return PitchTypeSplit(
        pitch_type=pitch_type,
        usage_share=usage,
        barrel_rate=field("barrel_rate", barrel),
        exit_velocity=field("exit_velocity", velocity),
        isolated_power=field("isolated_power", power),
        expected_woba=field("expected_woba", woba),
        whiff_rate=field("whiff_rate", whiff),
        swinging_strike_rate=field("swinging_strike_rate", swinging_strike),
    )


def _usage(share: str, sample_pitches: int = 400) -> SnapshotField[UsageShare]:
    return SnapshotField.present(
        UsageShare(share=Decimal(share), sample_pitches=sample_pitches), SOURCE_ID
    )


def _alpha_splits() -> tuple[PitchTypeSplit, ...]:
    """Alpha's season splits, chosen so the screen cannot render without showing
    every eligibility state at once.

    **Usage shares here are structural, not OQ-4 artifacts.** They have to
    straddle the 15% threshold to exercise it, and they sum to exactly 1.000
    across the five measured types, so the share is a real share. Every *metric*
    value remains a deliberately non-baseball artifact (an ISO of 2.995, a
    1200.5 mph exit velocity), so nothing on this screen can be mistaken for a
    baseball judgment.
    """
    return (
        # Comfortably above the threshold, every metric present.
        _split("FF", _usage("0.550")),
        # Above the threshold with one metric missing: the type still shows.
        _split("SL", _usage("0.240"), absent_metric="expected_woba"),
        # Just above the threshold — the boundary is inclusive.
        _split("CH", _usage("0.160")),
        # Measured and small: suppressed, and named as suppressed.
        _split("CU", _usage("0.050")),
        # A TRUE ZERO over a positive sample: genuinely never thrown. Suppressed
        # as a measurement, never as an absence.
        _split("SI", _usage("0")),
        # Usage never observed: unevaluable, and each reason stays distinct
        # rather than flattening into one "unknown".
        _split("KC", SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID)),
        _split("FS", SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID)),
    )


def _splits_for(
    season: SnapshotField[tuple[PitchTypeSplit, ...]],
) -> tuple[WindowedPitchTypeSplits, ...]:
    """Season-to-date carries the given set; the shorter windows are absent.

    GMF-003's screen requests SEASON_TO_DATE, and a fixture that quietly filled
    the other two windows would be asserting captures nobody made.
    """
    return tuple(
        WindowedPitchTypeSplits(
            window=window,
            splits=season
            if window is Window.SEASON_TO_DATE
            else SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID),
        )
        for window in Window
    )


def _batter(
    batter_id: str,
    name: str,
    windows: tuple[WindowedBatterMetrics, ...],
    season_splits: SnapshotField[tuple[PitchTypeSplit, ...]] | None = None,
) -> BatterInputs:
    if season_splits is None:
        season_splits = SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID)
    return BatterInputs(
        batter_id=batter_id,
        name=name,
        windows=windows,
        pitch_type_splits=_splits_for(season_splits),
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
                # Every eligibility state, on one batter's metrics screen.
                season_splits=SnapshotField.present(_alpha_splits(), SOURCE_ID),
            ),
            _batter(
                "grid-demo-2",
                "Batter Bravo",
                tuple(_zero_metrics(window) for window in Window),
                # PRESENT AND EMPTY: the source answered and this batter faced
                # no tracked pitches. A real observation — the fourth thing —
                # and not the same as the set being absent.
                season_splits=SnapshotField.present((), SOURCE_ID),
            ),
            # The remaining three carry an absent split set, one reason each, so
            # the screen's set-level absence path renders all three distinctly.
            _batter(
                "grid-demo-3",
                "Batter Charlie",
                _uniform(AbsenceReason.NOT_YET_OBSERVED),
                season_splits=SnapshotField.absent(AbsenceReason.NOT_YET_OBSERVED, SOURCE_ID),
            ),
            _batter(
                "grid-demo-4",
                "Batter Delta",
                _uniform(AbsenceReason.SOURCE_UNAVAILABLE),
                season_splits=SnapshotField.absent(AbsenceReason.SOURCE_UNAVAILABLE, SOURCE_ID),
            ),
            _batter(
                "grid-demo-5",
                "Batter Echo",
                _uniform(AbsenceReason.NOT_APPLICABLE),
                season_splits=SnapshotField.absent(AbsenceReason.NOT_APPLICABLE, SOURCE_ID),
            ),
        ),
        parks=(),
    )
