"""Tests of the validation of the stochastic workload model."""

import pytest

from satedge_simulator.domain.workload import Priority
from satedge_simulator.domain.workload_model import Range, WorkloadModel
from satedge_simulator.errors import ScenarioError


def test_the_defaults_are_the_ones_chosen_for_the_case_study() -> None:
    model = WorkloadModel(arrivals_per_hour=4.0)
    assert model.mean_interarrival_s == 900.0
    assert model.raw_size_gb == Range(2.0, 12.0)
    assert model.stages == (1, 3)
    assert model.deadline_after_release_s[Priority.URGENT] == 7200.0


@pytest.mark.parametrize(
    "changes",
    [
        {"arrivals_per_hour": 0.0},
        {"urgent_probability": 1.5},
        {"raw_size_gb": Range(0.0, 12.0)},
        {"acquisition_delay_s": Range(-1.0, 10.0)},
        {"stages": (0, 3)},
        {"stages": (3, 1)},
        {"origins": ()},
        {"deadline_after_release_s": {Priority.URGENT: 7200.0}},
    ],
)
def test_invalid_parameters_are_rejected(changes: dict[str, object]) -> None:
    arguments: dict[str, object] = {"arrivals_per_hour": 4.0, **changes}
    with pytest.raises(ScenarioError):
        WorkloadModel(**arguments)  # type: ignore[arg-type]


def test_a_range_needs_ordered_finite_bounds() -> None:
    with pytest.raises(ScenarioError):
        Range(2.0, 1.0)
    with pytest.raises(ScenarioError):
        Range(0.0, float("inf"))
