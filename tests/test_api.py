"""Tests of the facade, on the case study planned by the sequential heuristic."""

import json
import shutil
from pathlib import Path

import pytest

from satedge_simulator.api import (
    EVENTS_FILE,
    METRICS_FILE,
    SimulationResult,
    simulate_file,
)
from satedge_simulator.domain.lifecycle import RequestStatus
from satedge_simulator.errors import DocumentError, ScenarioError

EXAMPLE = Path(__file__).parent.parent / "examples" / "casostudio"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> tuple[SimulationResult, Path]:
    output = tmp_path_factory.mktemp("casostudio")
    return simulate_file(EXAMPLE / "scenario.yaml", output), output


def test_the_case_study_runs_and_its_delivery_passes_the_check(
    run: tuple[SimulationResult, Path],
) -> None:
    result, _ = run
    assert result.verified
    statuses = {r.status for r in result.outcome.records.values()}
    assert statuses == {RequestStatus.DELIVERED_ON_TIME}


def test_the_output_holds_the_event_log_and_the_metrics(
    run: tuple[SimulationResult, Path],
) -> None:
    result, output = run
    events = [
        json.loads(line)
        for line in (output / EVENTS_FILE).read_text(encoding="utf-8").splitlines()
    ]
    assert events[0] == {"type": "RequestArrived", "time": 0.0, "request_id": "R1"}
    delivered = [e for e in events if e["type"] == "RequestDelivered"]
    assert len(delivered) == len(result.outcome.records)
    metrics = json.loads((output / METRICS_FILE).read_text(encoding="utf-8"))
    assert metrics["verification"] == {"passed": True, "findings": []}
    assert metrics["violations"] == {}
    assert sum(c["delivered_on_time"] for c in metrics["requests"]) == len(delivered)
    assert metrics["outcomes"]["R1"]["status"] == "delivered_on_time"


def test_without_an_output_nothing_is_written(tmp_path: Path) -> None:
    scenario = copy_example(tmp_path)
    simulate_file(scenario)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        p.name for p in EXAMPLE.iterdir()
    )


def test_a_scenario_without_lead_time_needs_a_solver_with_a_time_limit(
    tmp_path: Path,
) -> None:
    scenario = copy_example(tmp_path)
    text = scenario.read_text(encoding="utf-8")
    scenario.write_text(
        text.replace("lead_time_s: 60", "lead_time_s: null"), encoding="utf-8"
    )
    with pytest.raises(ScenarioError, match="no lead time"):
        simulate_file(scenario)


def test_an_invalid_solver_file_is_a_document_error(tmp_path: Path) -> None:
    scenario = copy_example(tmp_path)
    (tmp_path / "solver.yaml").write_text(
        'schema_version: "1.0.0"\nmethod: magic\n', encoding="utf-8"
    )
    with pytest.raises(DocumentError):
        simulate_file(scenario)


def copy_example(directory: Path) -> Path:
    for file in EXAMPLE.iterdir():
        shutil.copy(file, directory / file.name)
    return directory / "scenario.yaml"
