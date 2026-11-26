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


def _sources(*, inside: Path | None = None, outside: Path | None = None) -> list[Path]:
    """The source files under ``inside`` (default: the package) and not under ``outside``."""
    return sorted(
        path
        for path in (inside or PACKAGE).rglob("*.py")
        if outside is None or outside not in path.parents
    )


def _id(path: Path) -> str:
    return str(path.relative_to(PACKAGE))


@pytest.mark.parametrize(
    "path", _sources(outside=PACKAGE / "planning" / "adapters" / "scheduler"), ids=_id
)
def test_only_the_adapter_imports_the_scheduler(path: Path) -> None:
    assert "satedge_workflow_scheduler" not in _imported_roots(path)


@pytest.mark.parametrize("path", _sources(outside=PACKAGE / "runtime"), ids=_id)
def test_only_the_runtime_imports_simpy(path: Path) -> None:
    assert "simpy" not in _imported_roots(path)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("path", _sources(inside=PACKAGE / "domain"), ids=_id)
def test_the_domain_does_not_depend_on_io(path: Path) -> None:
    assert not any(
        m.startswith("satedge_simulator.io") for m in _imported_modules(path)
    )
