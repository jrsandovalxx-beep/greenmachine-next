"""The shell's two standing rules, asserted on the strings themselves.

The visual language is D-003; the constraints are the prototype's: original
artwork only, and no remote request of any kind — a theme that phones home
for a font is not a theme, it is a dependency.
"""

from __future__ import annotations

from greenmachine.shell import (
    BLOT_CSS,
    BLOT_HTML,
    DIAL_CSS,
    FIELD_CSS,
    ORB_HTML,
    SHELL_CSS,
    TITLE_HTML,
    orb_html,
)

# The SVG namespace identifier is a constant string, never fetched.
_SVG_NAMESPACE = "http://www.w3.org/2000/svg"

_SHELL_ARTIFACTS = (SHELL_CSS, DIAL_CSS, ORB_HTML, TITLE_HTML, BLOT_CSS, BLOT_HTML, FIELD_CSS)


def test_the_shell_makes_no_remote_request() -> None:
    for artifact in _SHELL_ARTIFACTS:
        scrubbed = artifact.replace(_SVG_NAMESPACE, "")
        assert "http://" not in scrubbed
        assert "https://" not in scrubbed
        assert "https://" not in artifact
        assert "@import" not in artifact
        assert "url('http" not in artifact
        assert 'url("http' not in artifact


def test_the_shell_carries_the_three_shell_pieces() -> None:
    """Net, orb, blades: the background tile, the pulsing orb, and the neon
    tab styling must all be present for the screen to be the shell."""
    assert "data:image/svg+xml" in SHELL_CSS  # the net is inline artwork
    assert "gm-orb-pulse" in SHELL_CSS  # the orb breathes
    assert '[data-testid="stTab"]' in SHELL_CSS  # the tabs are the blades
    assert "gm-orb-seam" in ORB_HTML  # the fallback orb is seamed like a baseball


def test_the_logo_orb_is_inline_artwork_with_a_drawn_fallback() -> None:
    """D-107: the header mark is the ouroboros-around-a-baseball logo,
    injected as a data URI on the same pulsing circle — inline data, never a
    fetch — and with no asset the hand-drawn seam orb stands in."""
    logo = orb_html("data:image/png;base64,AAAA")
    assert "gm-orb" in logo  # the circle clip and the pulse still apply
    assert "gm-orb-img" in logo
    assert 'src="data:image/png;base64,AAAA"' in logo
    assert "gm-orb-seam" not in logo  # the painted seams yield to the mark
    scrubbed = logo.replace(_SVG_NAMESPACE, "")
    assert "http://" not in scrubbed
    assert "https://" not in scrubbed
    assert orb_html(None) == ORB_HTML


def test_the_blot_is_a_morphing_blob_not_a_wheel() -> None:
    """D-084: the loading blot imitates the console startup blotter — a blob
    whose border-radius keeps reshaping it — never the stock spinner."""
    assert "@keyframes gm-blot-morph" in BLOT_CSS
    assert BLOT_CSS.count("border-radius:") >= 4  # the shape keeps changing
    assert "animation: gm-blot-morph" in BLOT_CSS
    assert "gm-blot-blob" in BLOT_HTML
    assert "spinner" not in (BLOT_CSS + BLOT_HTML).lower()


def test_the_dial_is_a_drawn_ring_with_a_slot_rule_per_pair() -> None:
    """D-083: the ring and hub are drawn in CSS, and the motion is one
    ``:has()`` placement rule per (selected tab, item) pair — sixteen for the
    four tabs — with the transition doing the turn."""
    assert 'div[role="tablist"]::before' in DIAL_CSS  # the drawn ring
    assert 'div[role="tablist"]::after' in DIAL_CSS  # the hub
    assert DIAL_CSS.count(":has(") == 16
    assert DIAL_CSS.count("nth-of-type(") == 32  # each pair names both ends
    assert "transition: transform" in DIAL_CSS
    # every slot lands on the ring: the orbit transform chain appears 16 times
    assert DIAL_CSS.count("translate(-50%, -50%) rotate(") == 16


def test_the_shell_copies_no_console_artwork() -> None:
    """Inspired-by, never copied: no console maker's mark appears anywhere."""
    for artifact in _SHELL_ARTIFACTS:
        assert "xbox" not in artifact.lower()


def test_the_field_panel_draws_the_diamond_and_the_wind_blows() -> None:
    """D-084: the field panel is drawn artwork (no image fetch), and the
    wind flow bears the way the wind blows — compass readings name where it
    blows FROM, so the arrow is rotated one-eighty on."""
    from greenmachine.shell import field_wind_html

    assert "@keyframes gm-wind-drift" in FIELD_CSS
    html = field_wind_html(
        venue_name="Coors Field",
        detail_lines=(),
        wind_speed_mph=9.0,
        wind_direction="W",
    )
    # Wind from the west blows toward the east: bearing 90, and east is the
    # SVG's unrotated axis — the flow renders unrotated.
    assert "rotate(0.0" in html
    assert "gm-wind-flow" in html
    assert "wind 9 mph from the W" in html


def test_the_field_panel_speaks_field_words_on_the_measured_axis() -> None:
    """D-129 (PO): with the park's measured axis and the wind's from-bearing
    riding along, the line speaks field words and the flow rotates relative
    to the drawn field — axis and arrow agree."""
    from greenmachine.shell import field_wind_html

    html = field_wind_html(
        venue_name="Fenway Park",
        detail_lines=(),
        wind_speed_mph=12.0,
        wind_direction="N",
        wind_words="out to right",
        wind_from_degrees=0.0,
        axis_degrees=65.0,
    )
    assert "wind 12 mph out to right" in html
    assert "from the N" not in html
    # Field frame: toward = (0 + 180 - 65 - 90) = 25 degrees on the drawn field.
    assert "rotate(25.0" in html


def test_the_field_panel_keeps_the_compass_frame_without_an_axis() -> None:
    from greenmachine.shell import field_wind_html

    html = field_wind_html(
        venue_name="Coors Field",
        detail_lines=(),
        wind_speed_mph=9.0,
        wind_direction="W",
        wind_words=None,
    )
    assert "rotate(0.0" in html
    assert "wind 9 mph from the W" in html


def test_the_field_panel_states_a_roofed_venue_without_a_flow() -> None:
    from greenmachine.shell import field_wind_html

    html = field_wind_html(
        venue_name="Chase Field",
        detail_lines=(),
        wind_speed_mph=None,
        wind_direction=None,
        wind_absent_text="roofed — wind never reaches the field",
    )
    assert "gm-wind-flow" not in html
    assert "roofed — wind never reaches the field" in html
