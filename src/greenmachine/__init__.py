"""GreenMachine: a deterministic MLB home-run grading and research platform.

The package version is declared once, in ``pyproject.toml``. It is read here from
the installed distribution metadata rather than duplicated in source, so the two
can never drift apart.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("greenmachine")
except PackageNotFoundError as exc:  # pragma: no cover - only reachable when not installed
    message = (
        "The greenmachine distribution is not installed, so its version cannot be "
        "resolved. Install the project in editable mode first: make install"
    )
    raise RuntimeError(message) from exc

# D-157: staleness marker for the entrypoint's eviction guard. The deploy
# host can import this package before streamlit_app.py's first line runs,
# serving bytecode compiled from older sources; any module carrying this
# marker was necessarily loaded from current code. Bump on any deploy-cache
# incident so a stale serve is detectable (and evictable) in one getattr.
DEPLOY_EPOCH = 157

__all__ = ["DEPLOY_EPOCH", "__version__"]
