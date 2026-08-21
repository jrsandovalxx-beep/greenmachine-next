"""The main-screen shell (D-003, D-076): the original-Xbox visual language.

Everything here is a string of original, hand-written CSS/HTML — no Xbox logo,
icon, asset or menu graphic is copied, and nothing references a remote font,
image, stylesheet, script or CDN: the module is importable data so tests can
assert both rules directly, and the composition root only has to inject it.

Four pieces: the dark-emerald geometric net behind the page, the glowing
baseball-seamed orb beside the title, the neon blade styling that turns the
four live-board tabs into the console's menu bars, and the rotary menu
motion (D-083): the tabs ride a drawn ring, and switching tabs rotates the
chosen one into the front slot — pure CSS, ``:has()`` reading which tab is
selected, no script and no copied artwork.
"""

from __future__ import annotations

# A hand-drawn geometric mesh tile — a few polygon strokes on transparency,
# tiled faintly behind everything. Deliberately subtle: the reference's net is
# texture, not the subject.
_BACKGROUND_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='360' "
    "height='360'%3E%3Cg fill='none' stroke='%231c3a20' stroke-width='1'%3E"
    "%3Cpath d='M0 40 L120 0 L240 60 L360 20'/%3E"
    "%3Cpath d='M0 40 L60 160 L0 300'/%3E"
    "%3Cpath d='M120 0 L150 140 L60 160'/%3E"
    "%3Cpath d='M150 140 L240 60 L300 170 L360 120'/%3E"
    "%3Cpath d='M150 140 L190 260 L300 170'/%3E"
    "%3Cpath d='M60 160 L190 260 L120 360'/%3E"
    "%3Cpath d='M190 260 L330 300 L300 170'/%3E"
    "%3Cpath d='M330 300 L360 340'/%3E"
    "%3Cpath d='M0 300 L120 360'/%3E"
    "%3Cpath d='M240 60 L240 0'/%3E%3C/g%3E%3C/svg%3E"
)

SHELL_CSS = (
    "<style>\n"
    "/* the dark-emerald net behind everything */\n"
    ".stApp {\n"
    "  background-color: #07130a;\n"
    f'  background-image: url("{_BACKGROUND_SVG}");\n'
    "  background-size: 360px 360px;\n"
    "}\n"
    '[data-testid="stHeader"] { background: rgba(7, 19, 10, 0.85); }\n'
    "\n"
    "/* the glowing orb: a bright core sinking into deep emerald, with two\n"
    "   curved seams so it reads as a baseball, and a slow pulse */\n"
    ".gm-orb-wrap { display: flex; justify-content: center; padding-top: 18px; }\n"
    ".gm-orb {\n"
    "  position: relative; width: 150px; height: 150px; border-radius: 50%;\n"
    "  background: radial-gradient(circle at 35% 32%, #f0ffc8 0%, #c6ff4d 22%,"
    " #5fb214 52%, #145012 78%, #062006 100%);\n"
    "  box-shadow: 0 0 26px 8px rgba(155, 240, 11, 0.45),"
    " 0 0 90px 34px rgba(155, 240, 11, 0.18),"
    " inset 0 0 34px rgba(0, 0, 0, 0.45);\n"
    "  animation: gm-orb-pulse 4.5s ease-in-out infinite;\n"
    "}\n"
    "@keyframes gm-orb-pulse {\n"
    "  0%, 100% { box-shadow: 0 0 26px 8px rgba(155, 240, 11, 0.45),"
    " 0 0 90px 34px rgba(155, 240, 11, 0.18), inset 0 0 34px rgba(0, 0, 0, 0.45); }\n"
    "  50% { box-shadow: 0 0 36px 12px rgba(155, 240, 11, 0.65),"
    " 0 0 120px 44px rgba(155, 240, 11, 0.28), inset 0 0 34px rgba(0, 0, 0, 0.45); }\n"
    "}\n"
    ".gm-orb-seam {\n"
    "  position: absolute; top: 12px; bottom: 12px; width: 46%;\n"
    "  border: 3px solid rgba(6, 46, 12, 0.55); border-radius: 50%;\n"
    "}\n"
    ".gm-orb-seam.gm-left { left: 8px; border-right-color: transparent;"
    " border-top-color: transparent; transform: rotate(24deg); }\n"
    ".gm-orb-seam.gm-right { right: 8px; border-left-color: transparent;"
    " border-bottom-color: transparent; transform: rotate(24deg); }\n"
    "\n"
    "/* title and status line */\n"
    ".gm-title {\n"
    "  font-size: 3.1rem; font-weight: 800; letter-spacing: 0.05em;\n"
    "  color: #dcffb0; text-shadow: 0 0 22px rgba(155, 240, 11, 0.55);\n"
    "  margin: 6px 0 2px;\n"
    "}\n"
    ".gm-tagline { color: #9dc48c; font-size: 0.95rem; margin-bottom: 2px; }\n"
    ".gm-status { color: #6f8f63; font-size: 0.8rem; letter-spacing: 0.04em; }\n"
    "\n"
    "/* the tabs become the console's neon menu blades (1.62's tabs are\n"
    "   react-aria: role=tablist holding [data-testid=stTab] divs) */\n"
    '[data-testid="stTabs"] div[role="tablist"] {\n'
    "  gap: 12px; background: transparent; border-bottom: none;\n"
    "  padding: 6px 0 10px;\n"
    "}\n"
    '[data-testid="stTab"] {\n'
    "  background: rgba(18, 58, 22, 0.55); color: #b8e986;\n"
    "  border: 1px solid #2e5b23; border-radius: 7px;\n"
    "  padding: 8px 30px; font-weight: 700; letter-spacing: 0.14em;\n"
    "  text-transform: uppercase;\n"
    "  box-shadow: inset 0 0 14px rgba(155, 240, 11, 0.10);\n"
    "}\n"
    '[data-testid="stTab"]:hover {\n'
    "  background: rgba(44, 116, 38, 0.65); color: #eaffb0;\n"
    "}\n"
    '[data-testid="stTab"][aria-selected="true"] {\n'
    "  background: #9bf00b; color: #0d2405;\n"
    "  box-shadow: 0 0 20px rgba(155, 240, 11, 0.65);\n"
    "}\n"
    '[data-testid="stTab"] [class*="SelectionIndicator"] { display: none; }\n'
    "\n"
    "/* tables sit on the same deep green, framed faintly in neon */\n"
    '[data-testid="stDataFrame"] {\n'
    "  border: 1px solid #21491f; border-radius: 8px;\n"
    "  box-shadow: 0 0 18px rgba(155, 240, 11, 0.08);\n"
    "}\n"
    "</style>"
)

ORB_HTML = (
    '<div class="gm-orb-wrap"><div class="gm-orb">'
    '<div class="gm-orb-seam gm-left"></div>'
    '<div class="gm-orb-seam gm-right"></div>'
    "</div></div>"
)

TITLE_HTML = '<div class="gm-title">GreenMachine</div>'


# --------------------------------------------------------------------------
# D-083: the rotary menu motion
# --------------------------------------------------------------------------
#
# The four tabs sit on a ring like a rotary dial's numbers: the front slot is
# twelve o'clock, the rest trail down the ring's right shoulder, and when the
# selection changes every tab glides along the arc to its new slot — the ring
# appears to rotate the choice into place. The mechanism is one ``:has()``
# rule per (selected, item) pair: the selected tab's aria attribute is the
# only state the stylesheet reads, and the transition does the rest. Slots
# are 28° apart; the front tab is lit and largest, the trailing ones recede.
# Ring, hub and motion are drawn here — no console maker's marks, no remote
# asset.


_BLOT_MORPH = (
    "@keyframes gm-blot-morph {\n"
    "  0%, 100% { border-radius: 58% 42% 55% 45% / 52% 58% 42% 48%;"
    " transform: rotate(0deg) scale(1); }\n"
    "  25% { border-radius: 40% 60% 38% 62% / 60% 35% 65% 40%;"
    " transform: rotate(24deg) scale(1.06); }\n"
    "  50% { border-radius: 62% 38% 48% 52% / 38% 62% 40% 60%;"
    " transform: rotate(-14deg) scale(0.94); }\n"
    "  75% { border-radius: 45% 55% 60% 40% / 55% 45% 58% 42%;"
    " transform: rotate(10deg) scale(1.03); }\n"
    "}\n"
    "@keyframes gm-blot-core {\n"
    "  0%, 100% { transform: scale(0.82) rotate(0deg); opacity: 0.9; }\n"
    "  50% { transform: scale(1.08) rotate(40deg); opacity: 1; }\n"
    "}\n"
)

BLOT_CSS = (
    "<style>\n"
    + _BLOT_MORPH
    + ".gm-blot-wrap { display: flex; flex-direction: column; align-items: center;"
    " gap: 18px; padding: 28px 0 8px; }\n"
    ".gm-blot { width: 148px; height: 148px; position: relative;"
    " display: flex; align-items: center; justify-content: center; }\n"
    ".gm-blot-blob { position: absolute; inset: 0;"
    " background: radial-gradient(circle at 32% 28%, rgba(234,255,176,0.95),"
    " rgba(155,240,11,0.85) 38%, rgba(31,109,26,0.9) 78%);"
    " box-shadow: 0 0 44px rgba(155,240,11,0.55),"
    " inset 0 0 30px rgba(9,38,8,0.5);"
    " animation: gm-blot-morph 3.2s ease-in-out infinite; }\n"
    ".gm-blot-blob.gm-blot-echo { inset: 18px;"
    " background: radial-gradient(circle at 66% 70%, rgba(184,233,134,0.9),"
    " rgba(46,142,47,0.75) 55%, rgba(18,58,22,0.85));"
    " mix-blend-mode: screen; opacity: 0.85;"
    " animation: gm-blot-morph 3.2s ease-in-out infinite reverse; }\n"
    ".gm-blot-core { width: 34px; height: 34px; border-radius: 50%;"
    " background: radial-gradient(circle at 40% 35%, #f4ffd6, #9bf00b 60%, #2e5b23);"
    " box-shadow: 0 0 26px rgba(244,255,214,0.9);"
    " animation: gm-blot-core 1.6s ease-in-out infinite; }\n"
    ".gm-blot-label { color: #9bf00b; letter-spacing: 0.22em;"
    " text-transform: uppercase; font-weight: 700; font-size: 0.85rem;"
    " text-shadow: 0 0 12px rgba(155,240,11,0.5); }\n"
    "</style>"
)
"""Style for the slate-board loading blot (D-084)."""

BLOT_HTML = (
    '<div class="gm-blot-wrap">'
    '<div class="gm-blot">'
    '<div class="gm-blot-blob"></div>'
    '<div class="gm-blot-blob gm-blot-echo"></div>'
    '<div class="gm-blot-core"></div>'
    "</div>"
    '<div class="gm-blot-label">Building today&#39;s slate board&hellip;</div>'
    "</div>"
)
"""Markup for the slate-board loading blot (D-084)."""


_DIAL_STEP_DEG = 90
_DIAL_RADIUS_PX = 108
# scale and opacity by angular distance from the front slot: lit at front,
# receding down the shoulder, smallest and faintest at the back.
_DIAL_DEPTH: dict[int, tuple[float, float]] = {
    0: (1.06, 1.0),
    90: (0.88, 0.7),
    180: (0.74, 0.4),
}


def _dial_slot_rules() -> str:
    """One placement rule per (selected tab, item) pair — the whole motion is
    these sixteen rules plus the transition on the buttons."""
    rules: list[str] = []
    for selected in range(4):
        for item in range(4):
            # shortest path around the ring: offsets land at 0, +/-90 or 180
            offset = (item - selected) % 4
            if offset > 2:
                offset -= 4
            angle = offset * _DIAL_STEP_DEG
            scale, opacity = _DIAL_DEPTH[abs(angle)]
            rules.append(
                '[data-testid="stTabs"] div[role="tablist"]:has('
                f'> [data-testid="stTab"][aria-selected="true"]:nth-of-type({selected + 1})) '
                f'> [data-testid="stTab"]:nth-of-type({item + 1}) {{\n'
                f"  transform: translate(-50%, -50%) rotate({angle}deg) "
                f"translateY(-{_DIAL_RADIUS_PX}px) rotate({-angle}deg) scale({scale});\n"
                f"  opacity: {opacity};\n"
                f"  z-index: {90 - abs(angle)};\n"
                "}\n"
            )
    return "".join(rules)


DIAL_CSS = (
    "<style>\n"
    "/* the tab list becomes the rotary menu's ring */\n"
    '[data-testid="stTabs"] div[role="tablist"] {\n'
    "  position: relative; display: block; overflow: visible;\n"
    "  width: 340px; height: 284px; margin: 4px auto 0; padding: 0;\n"
    "}\n"
    "/* the ring the tabs ride — a faint drawn circle with a hub */\n"
    '[data-testid="stTabs"] div[role="tablist"]::before {\n'
    '  content: ""; position: absolute; left: 50%; top: 50%;\n'
    "  width: 216px; height: 216px; transform: translate(-50%, -50%);\n"
    "  border-radius: 50%; border: 1px solid rgba(155, 240, 11, 0.22);\n"
    "  box-shadow: 0 0 22px rgba(155, 240, 11, 0.10),"
    " inset 0 0 22px rgba(155, 240, 11, 0.06);\n"
    "}\n"
    '[data-testid="stTabs"] div[role="tablist"]::after {\n'
    '  content: ""; position: absolute; left: 50%; top: 50%;\n'
    "  width: 10px; height: 10px; transform: translate(-50%, -50%);\n"
    "  border-radius: 50%;\n"
    "  background: radial-gradient(circle at 35% 30%, #dcffb0, #5fb214 70%, #145012);\n"
    "  box-shadow: 0 0 10px rgba(155, 240, 11, 0.55);\n"
    "}\n"
    "/* every tab is parked at the ring's centre until its slot rule places\n"
    "   it; the transition turns a selection change into the dial's turn */\n"
    '[data-testid="stTab"] {\n'
    "  position: absolute; left: 50%; top: 50%; margin: 0;\n"
    "  white-space: nowrap;\n"
    "  transition: transform 0.55s cubic-bezier(0.22, 0.9, 0.24, 1),"
    " opacity 0.4s ease, background 0.3s ease, color 0.3s ease,"
    " box-shadow 0.3s ease;\n"
    "}\n"
    f"{_dial_slot_rules()}"
    "</style>"
)
