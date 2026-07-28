"""Placeholder test: the GMR-001 skeleton packages import (REBUILD_PLAN, GMR-001 scope 5).

GMR-002's pipeline dies on pytest exit code 5 (no tests collected), so this file
guarantees collection of at least one test until GMR-003 transplants the real suite,
which replaces the skeleton placeholders by design (PORT_MANIFEST v2).
"""

import importlib

import pytest

SUBPACKAGES = [
    "greenmachine",
    "greenmachine.common",
    "greenmachine.config",
    "greenmachine.domain",
    "greenmachine.evaluation",
    "greenmachine.scoring",
]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name: str) -> None:
    assert importlib.import_module(name).__name__ == name
