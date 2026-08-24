"""Wind resolution for the live board (SP-4, D-119): turn the forecast's
compass reading into the one number the tags need — how many miles per hour
of the wind blow toward a named field, signed.

The forecast names where the wind blows **from** (NWS convention); a field's
direction is a bearing from home plate (degrees true, ``PARK_ORIENTATION``
for the center-field axis, spray thirds off it for the corners). The
resolved component toward a field is

    speed * cos(bearing_from + 180 - field_bearing)

positive blowing out toward that field, negative blowing in from it. All
angles are degrees true; the cosine is computed in floating point and the
result stays a Decimal at the app's one-mph display precision.

Pure functions only: the pipeline parses the compass text when it builds the
game card, the view resolves against each batter's air field when it tags,
and neither side re-derives the other's half.
"""

from __future__ import annotations

import math
from decimal import Decimal

# The sixteen-point compass, degrees true. NWS forecast periods emit these
# (uppercase, occasionally lowercase); anything else — "Variable", calm, a
# garbled string — is an honest None, never a guessed direction.
_COMPASS_DEGREES: dict[str, Decimal] = {
    "N": Decimal("0"),
    "NNE": Decimal("22.5"),
    "NE": Decimal("45"),
    "ENE": Decimal("67.5"),
    "E": Decimal("90"),
    "ESE": Decimal("112.5"),
    "SE": Decimal("135"),
    "SSE": Decimal("157.5"),
    "S": Decimal("180"),
    "SSW": Decimal("202.5"),
    "SW": Decimal("225"),
    "WSW": Decimal("247.5"),
    "W": Decimal("270"),
    "WNW": Decimal("292.5"),
    "NW": Decimal("315"),
    "NNW": Decimal("337.5"),
}


def wind_from_degrees(direction_text: str | None) -> Decimal | None:
    """The compass reading as degrees true, or None when the text is not a
    sixteen-point direction. A direction that cannot be parsed must not
    become a wind read against an invented bearing (absence-first)."""
    if direction_text is None:
        return None
    return _COMPASS_DEGREES.get(direction_text.strip().upper())


def resolved_wind_mph(
    speed_mph: Decimal,
    wind_from: Decimal,
    field_bearing: Decimal,
) -> Decimal:
    """The signed component of the wind along one field's bearing: positive
    blowing out toward the field, negative blowing in from it. ``speed`` is
    the forecast sustained speed; gusts are not sourced and never enter."""
    toward = (float(wind_from) + 180.0 - float(field_bearing)) % 360.0
    component = math.cos(math.radians(toward))
    return Decimal(str(round(float(speed_mph) * component, 6)))


def spray_field_bearing(
    axis_bearing: Decimal,
    batting_side: str,
    field: str,
) -> Decimal:
    """The bearing of one spray third for one resolved batting side. Thirds
    split the ninety foul-line degrees into three: the pull corner centers
    thirty degrees off the axis (left field for a right-hander, right field
    for a left-hander), center rides the axis itself, and the opposite-field
    corner mirrors the pull one. ``field`` is "pull", "center" or "oppo";
    ``batting_side`` is the resolved side ("L" or "R", D-065)."""
    offset = {"pull": Decimal("-30"), "center": Decimal("0"), "oppo": Decimal("30")}[field]
    if batting_side == "L":
        offset = -offset
    bearing = axis_bearing + offset
    # Decimal's remainder truncates toward zero, so normalize by hand.
    while bearing < Decimal("0"):
        bearing += Decimal("360")
    while bearing >= Decimal("360"):
        bearing -= Decimal("360")
    return bearing
