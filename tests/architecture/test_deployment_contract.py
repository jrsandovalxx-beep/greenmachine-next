"""GM-030-r2 deployment-readiness contract for Streamlit Community Cloud.

The hosted app installs the repository-root ``requirements.txt``
automatically, so that file must carry exactly the bounded runtime/UI
dependencies — the project runtime dependencies plus the UI extra — and
never a development tool. (The legacy release-archive clause left with its
test in GMR-005: the rebuild has no release-archive mechanism.)
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = REPO_ROOT / "requirements.txt"

# The one local editable project-install line (GM-040-HF1): Community Cloud
# installs requirements.txt only, and the app resolves its version from
# installed distribution metadata — so the host must install the project
# itself. This is not a dependency; it is the deployment's self-install.
EDITABLE_SELF_INSTALL = "-e ."

APPROVED_REQUIREMENTS = (
    EDITABLE_SELF_INSTALL,
    # GMF-002 / D-062: floor 1.37 (`on_select`, stable `st.fragment`); the <2
    # ceiling is the major-version boundary, upgrades through staging first.
    "streamlit>=1.37,<2",
    # GMF-002 / D-059: the grid's Styler grading makes pandas a direct
    # dependency of the UI surface, declared rather than ridden transitively.
    "pandas>=2.1,<4",
    "PyYAML>=6,<7",
    "pydantic>=2,<3",
    # D-151 (2026-08-31): the floor moved deliberately — a real spec change
    # was the only lever that invalidates the host's cached environment
    # (comment-only bumps are ignored by it).
    "tzdata>=2025.1",
)

_DEV_ONLY_MARKERS = ("pytest", "hypothesis", "ruff", "mypy", "pre-commit", "types-")


def _requirement_lines() -> tuple[str, ...]:
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    return tuple(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def test_the_deployment_files_sit_at_the_repository_root() -> None:
    """GMR-005 replacement for the transplanted
    ``test_requirements_txt_sits_beside_the_entrypoint`` (register row 1,
    terminal state (b)): the same contract against the rebuild's own layout.
    Carried forward: the requirements file, the entrypoint, and the Streamlit
    configuration all sit at the repository root. Dropped: the GM-020
    evidence-bundle directory — OQ-7 (D-030) keeps evidence bundles in the
    frozen legacy repository, so that assertion is inapplicable here.
    """
    assert REQUIREMENTS.is_file()
    assert (REPO_ROOT / "streamlit_app.py").is_file()
    assert (REPO_ROOT / ".streamlit" / "config.toml").is_file()


def test_requirements_carry_exactly_the_approved_specifications() -> None:
    """The editable self-install first, then the same four bounded runtime/UI
    dependencies — nothing else."""
    assert _requirement_lines() == APPROVED_REQUIREMENTS


def test_the_editable_self_install_is_present_for_community_cloud() -> None:
    """GM-040-HF1 regression: without `-e .`, the hosted app crashes at import
    with PackageNotFoundError because no greenmachine distribution exists."""
    assert EDITABLE_SELF_INSTALL in _requirement_lines()


def test_requirements_carry_no_dev_or_test_dependency() -> None:
    rendered = " ".join(_requirement_lines()).lower()
    for marker in _DEV_ONLY_MARKERS:
        assert marker not in rendered, marker


def test_requirements_track_the_project_runtime_dependencies_plus_ui() -> None:
    """Dependency drift fails here: beyond the self-install line,
    requirements.txt must equal pyproject's runtime dependencies plus the
    [ui] extra, exactly."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = list(pyproject["project"]["dependencies"])
    ui_extra = list(pyproject["project"]["optional-dependencies"]["ui"])
    dependency_lines = [line for line in _requirement_lines() if line != EDITABLE_SELF_INSTALL]
    assert sorted(dependency_lines) == sorted(runtime + ui_extra)


def test_no_secret_shaped_deployment_file_exists() -> None:
    for pattern in ("secrets.toml", "*.pem", "*.key", ".env"):
        found = [
            path
            for path in REPO_ROOT.rglob(pattern)
            if ".venv" not in path.parts and "cleanvenv" not in path.parts
        ]
        assert found == [], f"secret-shaped file(s) present: {found}"


def test_the_deploy_bootstrap_sweeps_bytecode_before_the_package_imports(
    tmp_path: Path,
) -> None:
    """D-153: the 2026-08-31 host crash was stale bytecode inside the
    checkout outliving the source it was compiled from (the module's
    ``__file__`` named the current file while serving pre-D-143 code).
    The bootstrap sweeps every ``__pycache__`` under src/ on import and
    stops writing new ones — and it must import ahead of every
    ``greenmachine`` import in the entrypoint."""
    import deploy_bootstrap

    src = tmp_path / "src" / "pkg"
    nested = src / "live" / "__pycache__"
    nested.mkdir(parents=True)
    (nested / "pipeline.cpython-314.pyc").write_bytes(b"stale")
    source = src / "live" / "pipeline.py"
    source.write_text("# current", encoding="utf-8")
    removed, leftover = deploy_bootstrap.sweep_bytecode_caches(tmp_path)
    assert removed == 1
    assert leftover == ()
    assert not nested.exists()
    assert source.is_file()  # sources are never touched

    # D-154: the decisive guard — bytecode-cache lookups redirect to a
    # writable temp prefix, so a cache entry beside the source can never
    # be consulted again even when the tree is not app-writable.
    import importlib.util
    import sys

    assert sys.pycache_prefix == str(deploy_bootstrap.PYCACHE_PREFIX)
    redirected = importlib.util.cache_from_source(str(source))
    assert redirected.startswith(sys.pycache_prefix)

    entrypoint = (REPO_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    # D-155: the redirect must live in the entrypoint itself, ahead of the
    # bootstrap import — the host's root __pycache__ served the bootstrap
    # stale (D-153 bytecode under a current D-154 source), and a module
    # cannot protect its own cache. __main__ is never bytecode-cached.
    redirect_at = entrypoint.index('sys.pycache_prefix = tempfile.mkdtemp(prefix="gm_pycache_")')
    bootstrap_at = entrypoint.index("import deploy_bootstrap")
    first_package_at = entrypoint.index("from greenmachine")
    assert redirect_at < bootstrap_at < first_package_at
    # D-156: the redirect must be unconditional — the host arrives with
    # PYTHONPYCACHEPREFIX already set, and a guard that fires only on
    # None keeps serving the host's precompiled stale entries.
    assert 'or "gm_pycache_" not in sys.pycache_prefix' in entrypoint


def test_the_bootstrap_replaces_a_host_prefix_full_of_stale_bytecode(tmp_path: Path) -> None:
    """D-156: the host precompiles bytecode under PYTHONPYCACHEPREFIX —
    unchecked hash-based entries that serve stale code from current
    sources. Reproduced end to end: a fake host prefix carrying a stale
    deploy_bootstrap entry (no SWEPT_COUNT), the env var set, then the
    entrypoint's own sequence — the unconditional redirect first (it
    lives in __main__, never bytecode-cached, because no module can
    protect its own cache), then the import. The stale entry must be
    invisible and the fresh module loaded. This is the 2026-08-31
    incident mechanism and its fix."""
    import os
    import py_compile
    import sys

    from tests.network_guard.guarded_child import run_guarded_python

    repo_file = REPO_ROOT / "deploy_bootstrap.py"
    tag = sys.implementation.cache_tag
    host_prefix = tmp_path / "hostprefix"
    # PEP 3147 prefix layout: <prefix>/<abspath dirs>/<stem>.<tag>.pyc
    # (no __pycache__ segment under a prefix).
    mirrored = host_prefix / Path(str(repo_file.with_suffix(""))).relative_to("/")
    mirrored.parent.mkdir(parents=True)
    stale_source = tmp_path / "stale_bootstrap.py"
    stale_source.write_text("# stale pre-D-154 module: no SWEPT_COUNT\n", encoding="utf-8")
    py_compile.compile(
        str(stale_source),
        cfile=str(mirrored.parent / f"{mirrored.name}.{tag}.pyc"),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    ran = run_guarded_python(
        "-c",
        "import sys, tempfile; "
        "sys.pycache_prefix = tempfile.mkdtemp(prefix='gm_pycache_'); "
        "import deploy_bootstrap; "
        "assert 'gm_pycache_' in (sys.pycache_prefix or ''), sys.pycache_prefix; "
        "assert hasattr(deploy_bootstrap, 'SWEPT_COUNT'), 'stale module served'; "
        "print('FRESH')",
        env={
            **os.environ,
            "PYTHONPYCACHEPREFIX": str(host_prefix),
            "PYTHONPATH": str(REPO_ROOT),
        },
    )
    assert ran.returncode == 0, ran.stderr
    assert "FRESH" in ran.stdout


def test_deployment_documentation_names_the_entrypoint_and_requirements() -> None:
    documentation = (REPO_ROOT / "docs" / "STREAMLIT_PROTOTYPE.md").read_text(encoding="utf-8")
    assert "entrypoint | `streamlit_app.py`" in documentation
    assert "streamlit run streamlit_app.py" in documentation
    assert "requirements.txt" in documentation
    assert "automatically" in documentation
    # Community Cloud is never told to install the packaging extra.
    assert ".[ui]" not in documentation
    assert "install `.[ui]`" not in documentation
