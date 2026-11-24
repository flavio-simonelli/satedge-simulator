"""The dependency rules of the layers, checked on the import statements of the sources."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "satedge_simulator"


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _sources() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


@pytest.mark.parametrize("path", _sources(), ids=lambda p: str(p.relative_to(PACKAGE)))
def test_only_the_adapter_imports_the_scheduler(path: Path) -> None:
    adapter = PACKAGE / "planning" / "adapters" / "scheduler"
    if adapter in path.parents:
        return
    assert "satedge_workflow_scheduler" not in _imported_roots(path)


@pytest.mark.parametrize("path", _sources(), ids=lambda p: str(p.relative_to(PACKAGE)))
def test_only_the_runtime_imports_simpy(path: Path) -> None:
    if PACKAGE / "runtime" in path.parents:
        return
    assert "simpy" not in _imported_roots(path)
