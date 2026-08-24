"""SP-4 (D-119): the wind geometry's unit tests — compass parsing, the
signed out/in resolution, and the spray-third bearings."""

from __future__ import annotations

from decimal import Decimal

from greenmachine.live.wind import (
    resolved_wind_mph,
    spray_field_bearing,
    wind_from_degrees,
)


class TestCompassParsing:
    def test_all_sixteen_points_parse(self) -> None:
        assert wind_from_degrees("N") == Decimal("0")
        assert wind_from_degrees("NNE") == Decimal("22.5")
        assert wind_from_degrees("ESE") == Decimal("112.5")
        assert wind_from_degrees("S") == Decimal("180")
        assert wind_from_degrees("WSW") == Decimal("247.5")
        assert wind_from_degrees("NNW") == Decimal("337.5")

    def test_case_and_whitespace_are_forgiven(self) -> None:
        assert wind_from_degrees(" wsw ") == Decimal("247.5")

    def test_anything_else_is_an_absence(self) -> None:
        assert wind_from_degrees("Variable") is None
        assert wind_from_degrees("VRB") is None
        assert wind_from_degrees("XX") is None
        assert wind_from_degrees("") is None
        assert wind_from_degrees(None) is None


class TestResolution:
    def test_straight_out_is_the_full_speed(self) -> None:
        # Wind from the west (270) blows toward 90: straight out to a 90
        # axis. Positive is out.
        out = resolved_wind_mph(Decimal("10"), Decimal("270"), Decimal("90"))
        assert out == Decimal("10")

    def test_straight_in_is_the_negative_full_speed(self) -> None:
        # Wind from the east blows toward 270: straight in from a 90 axis.
        in_component = resolved_wind_mph(Decimal("10"), Decimal("90"), Decimal("90"))
        assert in_component == Decimal("-10")

    def test_pure_crosswind_resolves_to_zero(self) -> None:
        cross = resolved_wind_mph(Decimal("10"), Decimal("0"), Decimal("90"))
        assert abs(cross) < Decimal("0.0001")

    def test_diagonal_out_carries_the_cosine(self) -> None:
        # 45 degrees off the field line: cos(45) of the speed blows out.
        resolved = resolved_wind_mph(Decimal("10"), Decimal("225"), Decimal("90"))
        assert Decimal("7.0") < resolved < Decimal("7.2")

    def test_wraparound_geometry(self) -> None:
        # A north wind (from 0) blows toward 180; against a 357-degree axis
        # the out component is cos(180 - 357) = cos(-177), nearly full in.
        resolved = resolved_wind_mph(Decimal("8"), Decimal("0"), Decimal("357"))
        assert Decimal("-8.1") < resolved < Decimal("-7.9")


class TestSprayThirds:
    def test_right_hander_pull_is_left_of_the_axis(self) -> None:
        assert spray_field_bearing(Decimal("90"), "R", "pull") == Decimal("60")
        assert spray_field_bearing(Decimal("90"), "R", "center") == Decimal("90")
        assert spray_field_bearing(Decimal("90"), "R", "oppo") == Decimal("120")

    def test_left_hander_mirrors(self) -> None:
        assert spray_field_bearing(Decimal("90"), "L", "pull") == Decimal("120")
        assert spray_field_bearing(Decimal("90"), "L", "oppo") == Decimal("60")

    def test_bearings_wrap(self) -> None:
        assert spray_field_bearing(Decimal("5"), "R", "pull") == Decimal("335")
        assert spray_field_bearing(Decimal("357"), "L", "pull") == Decimal("27")
