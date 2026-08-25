"""The main-screen shell (D-003, D-076): the original-Xbox visual language.

Everything here is a string of original, hand-written CSS/HTML — no Xbox logo,
icon, asset or menu graphic is copied, and nothing references a remote font,
image, stylesheet, script or CDN: the module is importable data so tests can
assert both rules directly, and the composition root only has to inject it.

Four pieces: the dark-emerald geometric net behind the page, the glowing
orb beside the title, the neon blade styling that turns the
four live-board tabs into the console's menu bars, and the rotary menu
motion (D-083): the tabs ride a drawn ring, and switching tabs rotates the
chosen one into the front slot — pure CSS, ``:has()`` reading which tab is
selected, no script and no copied artwork.

The orb itself is the D-107 mark: an ouroboros ringed around a glowing
baseball — original artwork generated for this project, shipped as a repo
asset and injected by the composition root as a data URI, so the page still
makes no remote request. The hand-drawn seam orb below stands in when the
asset is absent.
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
    "/* the D-107 mark: the painted gradient gives way to the asset — the\n"
    "   circle clip and the pulsing glow stay */\n"
    ".gm-orb-img { display: block; background: none; object-fit: cover; }\n"
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


def orb_html(logo_data_uri: str | None) -> str:
    """The header orb (D-107). With the logo asset's data URI the orb is the
    ouroboros-baseball mark riding the same circle clip and pulse; without
    it the hand-drawn seam orb stands in. Either way the page makes no
    remote request — the URI is inline data, never a fetch.
    """
    if logo_data_uri is None:
        return ORB_HTML
    return (
        '<div class="gm-orb-wrap">'
        f'<img class="gm-orb gm-orb-img" src="{logo_data_uri}" '
        'alt="GreenMachine logo — an ouroboros around a glowing baseball">'
        "</div>"
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


FIELD_CSS = (
    "<style>\n"
    "@keyframes gm-wind-drift {\n"
    "  0% { transform: translateX(-70px); opacity: 0; }\n"
    "  15% { opacity: 0.85; }\n"
    "  80% { opacity: 0.85; }\n"
    "  100% { transform: translateX(70px); opacity: 0; }\n"
    "}\n"
    ".gm-field { display: flex; gap: 18px; align-items: center; }\n"
    ".gm-field svg { display: block; }\n"
    ".gm-field-info { color: #b8e986; font-size: 0.92rem; line-height: 1.6; }\n"
    ".gm-field-info .gm-field-venue { color: #eaffb0; font-weight: 700;"
    " letter-spacing: 0.04em; }\n"
    ".gm-field-info .gm-field-muted { color: #7d8f84; font-style: italic; }\n"
    ".gm-wind-streak { stroke: #eaffb0; stroke-width: 2; stroke-linecap: round;"
    " fill: none; }\n"
    ".gm-wind-streak-faint { stroke-width: 1.2; opacity: 0.55; }\n"
    ".gm-wind-flow { animation: gm-wind-drift 2.1s linear infinite; }\n"
    ".gm-wind-flow.gm-wind-lane-2 { animation-delay: 0.42s; }\n"
    ".gm-wind-flow.gm-wind-lane-3 { animation-delay: 0.84s; }\n"
    ".gm-wind-flow.gm-wind-lane-4 { animation-delay: 1.26s; }\n"
    ".gm-wind-flow.gm-wind-lane-5 { animation-delay: 1.68s; }\n"
    ".gm-wind-arrow { stroke: #f4ffd6; stroke-width: 2.4; }\n"
    ".gm-wind-arrowhead { fill: #f4ffd6; }\n"
    "</style>"
)
"""Style for the batter detail's drawn field panel (D-084)."""

_COMPASS_DEGREES = {
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}


def _wind_flow(toward_degrees: float) -> str:
    """The animated wind: streaking lanes drifting across the field plus an
    arrowhead, rotated to point the way the wind blows. ``toward_degrees``
    is the finished SVG rotation (clockwise from east, zero unrotated) —
    the caller resolves it from the compass reading, or from the park's
    measured axis so the arrow and the field words agree (D-129)."""
    toward = toward_degrees % 360.0
    # The lane offset lives on an outer group: a CSS animation transform
    # replaces the element's own transform attribute, so animating the same
    # element that carries the lane's placement would drop the lane at the
    # origin instead of across the field.
    lanes = "".join(
        f'<g transform="translate(120 {y})">'
        f'<g class="gm-wind-flow gm-wind-lane-{lane}">'
        '<line x1="-34" y1="0" x2="14" y2="0" class="gm-wind-streak" />'
        '<line x1="22" y1="0" x2="34" y2="0" class="gm-wind-streak gm-wind-streak-faint" />'
        "</g></g>"
        for lane, y in enumerate((52, 76, 100, 124, 148), start=1)
    )
    return (
        '<clipPath id="gm-field-clip">'
        '<path d="M 24 62 Q 120 -8 216 62 L 120 172 Z" />'
        "</clipPath>"
        f'<g transform="rotate({toward:.1f} 120 100)">'
        f'<g clip-path="url(#gm-field-clip)">{lanes}</g>'
        '<g transform="translate(120 100)">'
        '<line x1="-6" y1="0" x2="32" y2="0" class="gm-wind-arrow" />'
        '<path d="M 30 -6 L 44 0 L 30 6 Z" class="gm-wind-arrowhead" />'
        "</g>"
        "</g>"
    )


def field_wind_html(
    *,
    venue_name: str,
    detail_lines: tuple[str, ...],
    wind_speed_mph: float | None,
    wind_direction: str | None,
    wind_absent_text: str | None = None,
    wind_words: str | None = None,
    wind_from_degrees: float | None = None,
    axis_degrees: float | None = None,
) -> str:
    """The drawn field panel: the diamond with its warning track, wall,
    infield and mound; the live wind as a rotated, animated flow when a
    reading exists, or the plain reason it does not (roofed venue, or the
    source absent). Original artwork, inline. Per-park wall heights are not
    drawn: no ratified source for them exists yet.

    Per D-129 (PO): when the venue's measured home-to-center axis and the
    wind's from-bearing ride along, the flow rotates relative to the drawn
    field (center field up) and the line speaks field words — "wind out
    to right" — instead of the compass reading; without them the compass
    frame stands in, as before."""
    field = (
        '<svg width="240" height="200" viewBox="0 0 240 200"'
        ' xmlns="http://www.w3.org/2000/svg" role="img">'
        '<rect x="0" y="0" width="240" height="200" rx="10"'
        ' fill="rgba(9,38,8,0.55)" />'
        # the wall: a solid band along the outfield arc, its top edge lit
        '<path d="M 24 58 Q 120 -12 216 58 L 216 64 Q 120 -4 24 64 Z"'
        ' fill="rgba(46,91,35,0.9)" />'
        '<path d="M 24 58 Q 120 -12 216 58" fill="none"'
        ' stroke="rgba(234,255,176,0.5)" stroke-width="1.4" />'
        # warning track between the wall and the grass
        '<path d="M 24 64 Q 120 -4 216 64 L 208 74 Q 120 10 32 74 Z"'
        ' fill="rgba(122,92,20,0.4)" />'
        # grass
        '<path d="M 32 74 Q 120 10 208 74 L 120 172 Z" fill="rgba(31,109,26,0.55)" />'
        # infield dirt and the home-plate circle
        '<circle cx="120" cy="168" r="13" fill="rgba(122,92,20,0.5)" />'
        '<path d="M 120 100 L 160 136 L 120 168 L 80 136 Z"'
        ' fill="rgba(122,92,20,0.55)" />'
        '<path d="M 96 128 L 120 108 L 144 128 L 120 148 Z"'
        ' fill="rgba(31,109,26,0.6)" />'
        # mound
        '<circle cx="120" cy="139" r="5.5" fill="rgba(122,92,20,0.85)" />'
        '<rect x="116.5" y="137" width="7" height="2" fill="#eaffb0" opacity="0.8" />'
        # foul lines to the corners
        '<line x1="120" y1="170" x2="25" y2="62" stroke="rgba(234,255,176,0.55)"'
        ' stroke-width="1" />'
        '<line x1="120" y1="170" x2="215" y2="62" stroke="rgba(234,255,176,0.55)"'
        ' stroke-width="1" />'
        # bases and home plate
        '<rect x="117" y="97" width="6" height="6" fill="#eaffb0"'
        ' transform="rotate(45 120 100)" />'
        '<rect x="157" y="133" width="6" height="6" fill="#eaffb0"'
        ' transform="rotate(45 160 136)" />'
        '<rect x="77" y="133" width="6" height="6" fill="#eaffb0"'
        ' transform="rotate(45 80 136)" />'
        '<rect x="117" y="165" width="6" height="6" fill="#f4ffd6"'
        ' transform="rotate(45 120 168)" />'
    )
    if wind_speed_mph is not None and wind_direction is not None:
        if wind_from_degrees is not None and axis_degrees is not None:
            # Field frame: the wind blows toward (from + 180) true; the drawn
            # field puts the park axis up, and SVG zero points east — one
            # quarter-turn between the conventions, as in the compass path.
            toward = (wind_from_degrees + 180.0 - axis_degrees - 90.0) % 360.0
        else:
            degrees = _COMPASS_DEGREES.get(wind_direction.upper())
            toward = ((degrees if degrees is not None else 0.0) + 180.0 - 90.0) % 360.0
        flow = _wind_flow(toward)
        wind_line = (
            f"wind {wind_speed_mph:.0f} mph {wind_words}"
            if wind_words
            else f"wind {wind_speed_mph:.0f} mph from the {wind_direction.upper()}"
        )
        field += flow
    else:
        wind_line = wind_absent_text or "wind reading unavailable"
        field += (
            '<text x="120" y="104" text-anchor="middle" font-size="9"'
            ' fill="#7d8f84">no live wind</text>'
        )
    field += "</svg>"
    info = "".join(f"<div>{line}</div>" for line in detail_lines)
    return (
        '<div class="gm-field">'
        f"{field}"
        f'<div class="gm-field-info"><div class="gm-field-venue">{venue_name}</div>'
        f"{info}<div>{wind_line}</div></div>"
        "</div>"
    )
