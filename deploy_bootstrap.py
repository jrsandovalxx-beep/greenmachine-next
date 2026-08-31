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

Imported ahead of every greenmachine import in streamlit_app.py; the
module's own location anchors the repo root, so it works identically on
the host, in the sandbox, and under the test suites.
"""

from __future__ import annotations

import shutil
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
# bytecode from beside a source file again.
PYCACHE_PREFIX = Path(tempfile.mkdtemp(prefix="gm_pycache_"))
sys.pycache_prefix = str(PYCACHE_PREFIX)
SWEPT_COUNT, LEFTOVER_CACHES = sweep_bytecode_caches(Path(__file__).parent)
