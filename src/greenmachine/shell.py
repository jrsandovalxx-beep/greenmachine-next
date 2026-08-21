"""The main-screen shell (D-003, D-076): the original-Xbox visual language.

Everything here is a string of original, hand-written CSS/HTML — no Xbox logo,
icon, asset or menu graphic is copied, and nothing references a remote font,
image, stylesheet, script or CDN: the module is importable data so tests can
assert both rules directly, and the composition root only has to inject it.

Three pieces: the dark-emerald geometric net behind the page, the glowing
baseball-seamed orb beside the title, and the neon blade styling that turns
the four live-board tabs into the console's menu bars.
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
    "/* the tabs become the console's neon menu blades */\n"
    '[data-baseweb="tab-list"] {\n'
    "  gap: 12px; background: transparent; border-bottom: none;\n"
    "  padding: 6px 0 10px;\n"
    "}\n"
    'button[data-baseweb="tab"] {\n'
    "  background: rgba(18, 58, 22, 0.55); color: #b8e986;\n"
    "  border: 1px solid #2e5b23; border-radius: 7px;\n"
    "  padding: 8px 30px; font-weight: 700; letter-spacing: 0.14em;\n"
    "  text-transform: uppercase;\n"
    "  box-shadow: inset 0 0 14px rgba(155, 240, 11, 0.10);\n"
    "}\n"
    'button[data-baseweb="tab"]:hover {\n'
    "  background: rgba(44, 116, 38, 0.65); color: #eaffb0;\n"
    "}\n"
    'button[data-baseweb="tab"][aria-selected="true"] {\n'
    "  background: #9bf00b; color: #0d2405;\n"
    "  box-shadow: 0 0 20px rgba(155, 240, 11, 0.65);\n"
    "}\n"
    '[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }\n'
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
