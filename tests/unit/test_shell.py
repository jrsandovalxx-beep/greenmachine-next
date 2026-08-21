"""The shell's two standing rules, asserted on the strings themselves.

The visual language is D-003; the constraints are the prototype's: original
artwork only, and no remote request of any kind — a theme that phones home
for a font is not a theme, it is a dependency.
"""

from __future__ import annotations

from greenmachine.shell import ORB_HTML, SHELL_CSS, TITLE_HTML

# The SVG namespace identifier is a constant string, never fetched.
_SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def test_the_shell_makes_no_remote_request() -> None:
    for artifact in (SHELL_CSS, ORB_HTML, TITLE_HTML):
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
    assert 'button[data-baseweb="tab"]' in SHELL_CSS  # the tabs are the blades
    assert "gm-orb-seam" in ORB_HTML  # the orb is seamed like a baseball


def test_the_orb_copies_no_console_artwork() -> None:
    """Inspired-by, never copied: no Xbox mark appears anywhere."""
    for artifact in (SHELL_CSS, ORB_HTML, TITLE_HTML):
        assert "xbox" not in artifact.lower()
