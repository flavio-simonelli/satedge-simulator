"""Tests of the planner read from a solver file of the scheduler."""

from pathlib import Path

import pytest

from satedge_simulator.errors import DocumentError
from satedge_simulator.planning.adapters.scheduler.config import load_planner

EXAMPLE = Path(__file__).parents[3] / "examples" / "casostudio"


def test_the_milp_gives_its_time_limit_as_lead_time() -> None:
    configured = load_planner(EXAMPLE / "milp.yaml", horizon_s=28800.0)
    assert configured.time_limit_s == 60.0
    assert configured.hard_deadlines


def test_the_sequential_heuristic_has_no_time_limit() -> None:
    configured = load_planner(EXAMPLE / "solver.yaml", horizon_s=28800.0)
    assert configured.time_limit_s is None
    assert configured.hard_deadlines


def test_an_invalid_solver_file_is_reported_in_italian(tmp_path: Path) -> None:
    path = tmp_path / "solver.yaml"
    path.write_text('schema_version: "1.0.0"\nmethod: magic\n', encoding="utf-8")
    with pytest.raises(DocumentError, match="file del solver non valido"):
        load_planner(path, horizon_s=100.0)
