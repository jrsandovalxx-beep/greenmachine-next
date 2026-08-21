"""Grid-surface runner: render_grid without the main page around it.

The main screen is the Xbox shell plus the live board (D-076); the demo
surfaces are verified on their own, exactly as the page tests always asserted
them — at the element boundary.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit_app

streamlit_app.render_grid()
