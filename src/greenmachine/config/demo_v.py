"""Demonstration violation (GMR-003 criterion 7, config boundary): forbidden stdlib import."""

import os

CWD_NAME: str = os.path.basename(os.getcwd())
