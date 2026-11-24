"""Tests of the scenario file, on the case study example and on small broken scenarios."""

from pathlib import Path

import pytest

from satedge_simulator.errors import DocumentError
from satedge_simulator.io.scenario import load_scenario

EXAMPLE = Path(__file__).parents[2] / "examples" / "casostudio" / "scenario.yaml"


def test_case_study_scenario_loads_completely() -> None:
    loaded = load_scenario(EXAMPLE)
    scenario = loaded.scenario
    assert len(scenario.constellation.satellites) == 18
    assert len(scenario.requests) == 8
    assert scenario.settings.end_s == 28800.0
    assert scenario.lead_time_s is None
    assert loaded.solver_path.name == "solver.yaml"
    assert loaded.solver_path.is_file()


def test_every_request_origin_is_a_satellite_of_the_case_study() -> None:
    scenario = load_scenario(EXAMPLE).scenario
    assert all(scenario.constellation.is_satellite(r.origin) for r in scenario.requests)


def test_missing_referenced_file_names_the_file(tmp_path: Path) -> None:
    text = EXAMPLE.read_text(encoding="utf-8").replace(
        "workload: workload.yaml", "workload: nope.yaml"
    )
    (tmp_path / "scenario.yaml").write_text(text, encoding="utf-8")
    for name in ("topology.yaml", "contact_plan.yaml", "solver.yaml"):
        (tmp_path / name).write_text(
            (EXAMPLE.parent / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    with pytest.raises(DocumentError, match="nope.yaml"):
        load_scenario(tmp_path / "scenario.yaml")


def test_missing_solver_file_is_an_error(tmp_path: Path) -> None:
    text = EXAMPLE.read_text(encoding="utf-8").replace(
        "solver: solver.yaml", "solver: absent.yaml"
    )
    for name in ("topology.yaml", "contact_plan.yaml", "workload.yaml", "solver.yaml"):
        (tmp_path / name).write_text(
            (EXAMPLE.parent / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "scenario.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(DocumentError, match="absent.yaml"):
        load_scenario(tmp_path / "scenario.yaml")


def test_unknown_field_in_the_scenario_is_rejected(tmp_path: Path) -> None:
    text = EXAMPLE.read_text(encoding="utf-8") + "speed: 3\n"
    for name in ("topology.yaml", "contact_plan.yaml", "workload.yaml", "solver.yaml"):
        (tmp_path / name).write_text(
            (EXAMPLE.parent / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "scenario.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(DocumentError, match="scenario.yaml"):
        load_scenario(tmp_path / "scenario.yaml")
