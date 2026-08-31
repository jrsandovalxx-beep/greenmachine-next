"""Deploy bootstrap — runs before any ``greenmachine`` import (D-153).

The 2026-08-31 crash: the host's checkout carried the current
``pipeline.py`` (its sha256 matched the committed blob, git clean) while
the imported module still served the pre-D-143 code. The layer that can
do that is bytecode caching inside the checkout tree: ``__main__``
(streamlit_app.py) is always compiled fresh, but imported packages load
from ``__pycache__`` beside the source — a cache that survives git syncs
and the host's environment rebuilds, and that a stale entry can poison.
(Verified off-host: an unchecked hash-based .pyc serves its stale code
while the module's ``__file__`` still names the current source.)

Two permanent guards, both cheap:

1. Sweep every ``__pycache__`` under ``src/`` on every script run, before
   the package imports — a stale entry never survives to be loaded.
2. ``sys.dont_write_bytecode`` — the app stops writing new bytecode into
   the checkout, so the poisoned layer cannot regrow between deploys.

Imported first in streamlit_app.py's first-party block; the module's own
location anchors the repo root, so it works identically on the host, in
the sandbox, and under the test suites.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def sweep_bytecode_caches(root: Path) -> int:
    """Remove every ``__pycache__`` directory under ``root/src``.

    Returns the number of directories removed. Only the source tree is
    swept — the checkout's only import-time bytecode layer; the
    interpreter's own caches elsewhere are untouched.
    """
    removed = 0
    src = root / "src"
    if src.is_dir():
        for cache_dir in sorted(src.glob("**/__pycache__")):
            shutil.rmtree(cache_dir, ignore_errors=True)
            removed += 1
    return removed


sys.dont_write_bytecode = True
sweep_bytecode_caches(Path(__file__).parent)
