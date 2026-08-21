"""Metrics-surface runner: render_metrics_screen without the main page (D-076)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit_app

from greenmachine.fixtures import grid_demo_snapshot

streamlit_app.render_metrics_screen(grid_demo_snapshot())
