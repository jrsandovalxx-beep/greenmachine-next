"""Parks-surface runner: render_parks_screen without the main page (D-076)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit_app

streamlit_app.render_parks_screen()
