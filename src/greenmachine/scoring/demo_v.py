"""Demonstration violation (GMR-003 criterion 7, scoring boundary): float arithmetic."""

WEIGHT: float = 0.5


def scaled(points: int) -> float:
    """Scoring must never touch a float; this deliberately does."""
    return points * WEIGHT
