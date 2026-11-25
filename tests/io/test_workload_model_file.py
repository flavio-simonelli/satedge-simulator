"""Tests of the section ``workload_model`` of a scenario file."""

import shutil
from pathlib import Path

import pytest

from satedge_simulator.domain.workload_model import Range
from satedge_simulator.errors import DocumentError
from satedge_simulator.io.scenario import load_scenario

EXAMPLE = Path(__file__).parents[2] / "examples" / "casostudio"


def test_the_stochastic_example_loads_its_model_and_seed() -> None:
    scenario = load_scenario(EXAMPLE / "scenario-stocastico.yaml").scenario
    model = scenario.workload_model
    assert model is not None
    assert model.arrivals_per_hour == 4.0
    assert model.work_s_per_gb == Range(12.0, 24.0)
    assert model.origins is None
    assert scenario.requests == ()
    assert scenario.settings.seed == 123_456_789


def test_a_scenario_needs_a_workload(tmp_path: Path) -> None:
    for file in EXAMPLE.iterdir():
        shutil.copy(file, tmp_path / file.name)
    text = (tmp_path / "scenario.yaml").read_text(encoding="utf-8")
    (tmp_path / "scenario.yaml").write_text(
        text.replace("workload: workload.yaml\n", ""), encoding="utf-8"
    )
    with pytest.raises(DocumentError, match="serve un carico"):
        load_scenario(tmp_path / "scenario.yaml")


def test_an_invalid_model_names_the_file(tmp_path: Path) -> None:
    for file in EXAMPLE.iterdir():
        shutil.copy(file, tmp_path / file.name)
    path = tmp_path / "scenario-stocastico.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("arrivals_per_hour: 4", "arrivals_per_hour: -4"), encoding="utf-8"
    )
    with pytest.raises(DocumentError, match="tasso di arrivo"):
        load_scenario(path)
