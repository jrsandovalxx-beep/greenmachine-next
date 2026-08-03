"""GreenMachine deployment shell — name, environment, version, commit.

GMR-004 submission 1 (REBUILD_PLAN §GMR-004): a minimal Streamlit page that
renders exactly four fields and no product screens. GreenMachine tallies
criteria met and thresholds passed (D-015/D-017); this shell displays none of
that — it exists so the staging deployment can be verified end to end.
"""

from __future__ import annotations

import os
import subprocess
from importlib import metadata
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent

# The canonical non-production configuration directory (GM-041.5). The shell
# loads no configuration and renders no product screen; this constant exists
# because the config-location contract pins every repository-root consumer to
# the canonical path — never to a copy under the test tree.
NONPRODUCTION_CONFIG_DIR = REPO_ROOT / "config" / "nonproduction"


def _secret(key: str) -> str:
    """Read one value from Streamlit secrets, tolerating their absence.

    Local runs have no secrets source, and Streamlit raises on any secrets
    access when none exists; a missing secret must never crash the shell.
    """
    try:
        return str(st.secrets.get(key, "")).strip()
    except (FileNotFoundError, KeyError):
        return ""


def bridge_secrets_into_environment() -> None:
    """Fill absent ``GM_*`` environment variables from Streamlit secrets.

    Streamlit Community Cloud configures an app through its secrets store,
    not through environment variables. The bridge fills only absent keys, so
    a real environment variable always wins and the commit resolution order
    stays exactly as REBUILD_PLAN §GMR-004 defines it: git, then
    ``GM_COMMIT``, then ``unknown``.
    """
    for key in ("GM_ENVIRONMENT", "GM_COMMIT"):
        if not os.environ.get(key):
            value = _secret(key)
            if value:
                os.environ[key] = value


def resolve_environment() -> str:
    """The configured environment label, with an explicit ``local`` fallback.

    ``staging`` and ``production`` are configuration values (``GM_ENVIRONMENT``);
    when nothing is configured the shell says ``local`` rather than guessing.
    """
    return os.environ.get("GM_ENVIRONMENT", "").strip() or "local"


def resolve_version() -> str:
    """Installed package metadata, with an explicit ``unknown`` fallback."""
    try:
        return metadata.version("greenmachine")
    except metadata.PackageNotFoundError:
        return "unknown"


def resolve_commit() -> str:
    """The displayed commit, resolved git-first (REBUILD_PLAN §GMR-004).

    1. ``git rev-parse --short HEAD`` when a git checkout is present —
       including detached HEAD, which is a valid state with a valid SHA;
    2. else ``GM_COMMIT``, displayed with the explicit ``(env)`` provenance
       marker so a reader can see the value came from configuration, not the
       checkout — a stale environment variable can never mask a live checkout;
    3. otherwise the literal ``unknown``. Never a crash.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
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
    if env_value:
        return f"{env_value} (env)"
    return "unknown"


def main() -> None:
    st.set_page_config(page_title="GreenMachine", layout="centered")
    # GMR-004 submission 2 redeploy marker (criterion 7), doubling as the
    # observed-route diagnostic the reviewer required: it records whether the
    # GM_* keys reached os.environ before the bridge ran — i.e. whether the
    # host already exports root-level secrets as environment variables and the
    # bridge is a no-op here. Removed again by the criterion 8 rollback.
    watched = ("GM_ENVIRONMENT", "GM_COMMIT")
    pre_bridge = {key: key in os.environ for key in watched}
    bridge_secrets_into_environment()
    bridge_wrote = [key for key in watched if key in os.environ and not pre_bridge[key]]
    st.title("GreenMachine")
    st.caption("Deployment shell (REBUILD_PLAN §GMR-004) — no product screens.")
    st.markdown(f"**Environment:** {resolve_environment()}")
    st.markdown(f"**Version:** {resolve_version()}")
    st.markdown(f"**Commit:** {resolve_commit()}")
    st.caption(
        "GMR004-S2 redeploy marker — pre-bridge os.environ: "
        f"GM_ENVIRONMENT {'present' if pre_bridge['GM_ENVIRONMENT'] else 'absent'}, "
        f"GM_COMMIT {'present' if pre_bridge['GM_COMMIT'] else 'absent'}; "
        f"bridge wrote: {', '.join(bridge_wrote) if bridge_wrote else 'nothing'}"
    )


if __name__ == "__main__":
    main()
