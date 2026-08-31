"""Deploy bootstrap — runs before any ``greenmachine`` import (D-153/D-154).

The 2026-08-31 crash: the host's checkout carried the current
``pipeline.py`` (its sha256 matched the committed blob, git clean) while
the imported module still served the pre-D-143 code. The layer that can
do that is bytecode caching beside the source: ``__main__``
(streamlit_app.py) is always compiled fresh, but imported packages load
from ``__pycache__`` directories that survive the host's git syncs and
its environment rebuilds (D-149/D-151 rebuilt the venv; the poison lived
outside it). Reproduced off-host: an unchecked hash-based .pyc serves its
stale code while the module's ``__file__`` still names the current
source. The D-153 sweep alone could not remove them — the deployed
failure persisted — because those directories are not writable by the
app process, so D-154 adds the decisive guard:

``sys.pycache_prefix`` redirects the interpreter's entire bytecode-cache
layer to a fresh writable temp root. Every import after this module
resolves its cache under the prefix, never beside the source — the stale
entries become invisible whether or not they can be deleted, and normal
bytecode caching keeps working inside the prefix. The sweep stays as
hygiene for trees the app CAN write.

D-155 moved the redirect itself into the entrypoint: D-154 kept it here,
and the host's root ``__pycache__`` served THIS module from D-153
bytecode — a module cannot protect its own cache. ``__main__``
(streamlit_app.py) is never bytecode-cached, so the redirect there is
the one line of the guard the host must execute fresh. D-156 then made
the redirect unconditional in both places: the host arrives with
``PYTHONPYCACHEPREFIX`` already set (a root-owned precompiled tree),
and D-155's guarded form — fire only when the prefix is None — skipped
exactly when it mattered. This module keeps the sweep and the forensics
constants the failure surface prints.

Imported ahead of every greenmachine import in streamlit_app.py; the
module's own location anchors the repo root, so it works identically on
the host, in the sandbox, and under the test suites.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def sweep_bytecode_caches(root: Path) -> tuple[int, tuple[str, ...]]:
    """Remove every ``__pycache__`` directory under ``root/src``.

    Returns ``(removed, leftover)`` — leftover names the directories that
    would not delete (a tree the app cannot write), so the failure
    surface can name them instead of pretending the sweep worked.
    """
    removed = 0
    leftover: list[str] = []
    src = root / "src"
    if src.is_dir():
        for cache_dir in sorted(src.glob("**/__pycache__")):
            shutil.rmtree(cache_dir, ignore_errors=True)
            if cache_dir.exists():
                leftover.append(str(cache_dir))
            else:
                removed += 1
    return removed, tuple(leftover)


# The prefix redirect comes first: from this line on, no import ever reads
# bytecode from beside a source file again. Unconditional (D-156): the
# host can arrive with PYTHONPYCACHEPREFIX already set — a precompiled,
# root-owned cache tree whose stale entries a guarded redirect keeps
# serving. Only a prefix this process created is trusted; anything else
# is replaced.
if sys.pycache_prefix is None or "gm_pycache_" not in sys.pycache_prefix:
    sys.pycache_prefix = tempfile.mkdtemp(prefix="gm_pycache_")
PYCACHE_PREFIX = Path(sys.pycache_prefix)
SWEPT_COUNT, LEFTOVER_CACHES = sweep_bytecode_caches(Path(__file__).parent)


def _deploy_epoch() -> str:
    """The deploy epoch is the checkout's own commit sha (D-162) — the
    same read the entrypoint and the package marker make, so the three
    can never drift: git first, then GM_COMMIT, else "unknown"."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
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


# D-157/D-158/D-162: staleness marker for the entrypoint's eviction guard
# — see the matching marker in greenmachine/__init__.py. A pre-loaded
# module whose marker misses the entrypoint's read is by definition stale
# and gets evicted — at most once per epoch (D-159) — before the real
# imports run. Since D-162 the marker is the commit sha itself, read at
# import time: a module loaded from old code carries the old sha, and no
# one can forget to bump it — the D-160/D-161 deploy forgot the literal
# 159 bump, and the PicklingError returned within the hour.
DEPLOY_EPOCH = _deploy_epoch()
