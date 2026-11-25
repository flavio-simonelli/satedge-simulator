"""Tests of the plan of an epoch."""

import math

import pytest

from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.errors import ScenarioError


def test_action_spans_must_be_ordered_and_finite() -> None:
    with pytest.raises(ScenarioError):
        PlannedTask("R1", 0, "A", start_s=10.0, end_s=10.0)
    with pytest.raises(ScenarioError):
        PlannedTransfer("R1", 0, "A", "B", start_s=-1.0, end_s=5.0)
    with pytest.raises(ScenarioError):
        PlannedTask("R1", 0, "A", start_s=0.0, end_s=math.inf)


def test_a_task_appears_once() -> None:
    task = PlannedTask("R1", 0, "A", 0.0, 10.0)
    with pytest.raises(ScenarioError, match="più volte"):
        EpochPlan(tasks=(task, PlannedTask("R1", 0, "B", 20.0, 30.0)))


def test_plan_arrival_must_be_nonnegative_or_infinite() -> None:
    with pytest.raises(ScenarioError):
        EpochPlan(plan_arrival_s={"A": -1.0})
    plan = EpochPlan(plan_arrival_s={"A": 5.0, "B": math.inf})
    assert plan.plan_arrival_s["B"] == math.inf


def test_plan_arrival_mapping_is_read_only() -> None:
    source = {"A": 5.0}
    plan = EpochPlan(plan_arrival_s=source)
    source["A"] = 99.0
    assert plan.plan_arrival_s["A"] == 5.0
    with pytest.raises(TypeError):
        plan.plan_arrival_s["A"] = 1.0  # type: ignore[index]


def test_actions_are_grouped_by_satellite_in_start_order() -> None:
    plan = EpochPlan(
        tasks=(
            PlannedTask("R2", 0, "A", 50.0, 60.0),
            PlannedTask("R1", 0, "A", 10.0, 20.0),
            PlannedTask("R1", 1, "B", 30.0, 40.0),
        ),
        transfers=(PlannedTransfer("R1", 1, "A", "GS", 25.0, 26.0),),
    )
    assert [t.request_id for t in plan.tasks_of("A")] == ["R1", "R2"]
    assert plan.tasks_of("C") == ()
    assert len(plan.transfers_from("A")) == 1
    assert plan.transfers_from("GS") == ()
