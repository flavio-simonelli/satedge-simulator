"""Tests of the types of the planner port."""

import pytest

from satedge_simulator.domain.plan import EpochPlan, PlannedTask
from satedge_simulator.errors import PlannerError
from satedge_simulator.planning.ports import PlanningDecision


def test_a_request_cannot_be_accepted_and_rejected() -> None:
    plan = EpochPlan(tasks=(PlannedTask("R1", 0, "A", 0.0, 10.0),))
    with pytest.raises(PlannerError, match="R1"):
        PlanningDecision(plan=plan, rejected={"R1": "no window"})


def test_rejections_are_kept_apart_from_the_accepted_plan() -> None:
    plan = EpochPlan(tasks=(PlannedTask("R1", 0, "A", 0.0, 10.0),))
    decision = PlanningDecision(
        plan=plan, rejected={"R2": "deadline"}, solver_time_s=1.5
    )
    assert decision.rejected["R2"] == "deadline"
    with pytest.raises(TypeError):
        decision.rejected["R3"] = "x"  # type: ignore[index]


def test_solver_time_must_be_valid() -> None:
    with pytest.raises(PlannerError):
        PlanningDecision(plan=EpochPlan(), solver_time_s=-1.0)
