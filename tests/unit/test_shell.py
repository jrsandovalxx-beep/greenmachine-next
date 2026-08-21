"""The shell's two standing rules, asserted on the strings themselves.

The visual language is D-003; the constraints are the prototype's: original
artwork only, and no remote request of any kind — a theme that phones home
for a font is not a theme, it is a dependency.
"""

from __future__ import annotations

from greenmachine.shell import BLOT_CSS, BLOT_HTML, DIAL_CSS, ORB_HTML, SHELL_CSS, TITLE_HTML

# The SVG namespace identifier is a constant string, never fetched.
_SVG_NAMESPACE = "http://www.w3.org/2000/svg"

_SHELL_ARTIFACTS = (SHELL_CSS, DIAL_CSS, ORB_HTML, TITLE_HTML, BLOT_CSS, BLOT_HTML)


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
    assert "gm-orb-seam" in ORB_HTML  # the orb is seamed like a baseball


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
