"""GreenMachine: a deterministic MLB home-run grading and research platform.

The package version is declared once, in ``pyproject.toml``. It is read here from
the installed distribution metadata rather than duplicated in source, so the two
can never drift apart.
"""

from __future__ import annotations

import os
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("greenmachine")
except PackageNotFoundError as exc:  # pragma: no cover - only reachable when not installed
    message = (
        "The greenmachine distribution is not installed, so its version cannot be "
        "resolved. Install the project in editable mode first: make install"
    )
    raise RuntimeError(message) from exc


def _deploy_epoch() -> str:
    """The deploy epoch is the checkout's own commit sha (D-162) — the
    same read the entrypoint and the bootstrap marker make, so the three
    can never drift: git first, then GM_COMMIT, else "unknown". The
    package lives at <root>/src/greenmachine, so the checkout root is
    three parents up from this file."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed is not None and completed.returncode == 0 and completed.stdout.strip():
        return completed.stdout.strip()
    env_value = os.environ.get("GM_COMMIT", "").strip()
    return env_value or "unknown"


# D-157/D-162: staleness marker for the entrypoint's eviction guard. The
# deploy host can import this package before streamlit_app.py's first
# line runs, serving modules from an older commit; the marker stamps WHEN
# this module was loaded. Since D-162 it is the commit sha itself, read
# at import time — a stale pre-load carries the old sha by construction,
# and no deploy can forget to bump a literal (the D-160/D-161 deploy did,
# and the PicklingError returned within the hour).
DEPLOY_EPOCH = _deploy_epoch()

__all__ = ["DEPLOY_EPOCH", "__version__"]
