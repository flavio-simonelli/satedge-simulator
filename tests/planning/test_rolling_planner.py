"""Tests of the rolling planner, with a planner written by hand that decides what it is told."""

from dataclasses import dataclass, field

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.plan import EpochPlan, PlannedTask
from satedge_simulator.domain.topology import (
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.domain.workload import Priority, RequestSpec, TaskSpec
from satedge_simulator.errors import PlannerError, StateError
from satedge_simulator.planning.epochs import Epoch
from satedge_simulator.planning.ports import PlanningDecision, PlanningSnapshot
from satedge_simulator.planning.rolling_planner import RollingPlanner


@dataclass
class ScriptedPlanner:
    """Accepts the requests in ``accept``, rejects the others, and fails when asked to."""

    accept: set[str] = field(default_factory=set)
    fail: bool = False
    calls: list[PlanningSnapshot] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "scripted"

    def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
        self.calls.append(snapshot)
        if self.fail:
            raise PlannerError("no solution in time")
        accepted = [r for r in snapshot.new_requests if r.id in self.accept]
        rejected = {
            r.id: "not scheduled"
            for r in snapshot.new_requests
            if r.id not in self.accept
        }
        tasks = tuple(
            PlannedTask(
                r.id, 0, r.origin, start_s=r.release_s + 10.0, end_s=r.release_s + 20.0
            )
            for r in accepted
        )
        return PlanningDecision(plan=EpochPlan(tasks=tasks), rejected=rejected)


def request(request_id: str, release_s: float = 0.0) -> RequestSpec:
    return RequestSpec(
        id=request_id,
        priority=Priority.URGENT,
        origin="A",
        arrival_s=release_s,
        release_s=release_s,
        deadline_s=10_000.0,
        raw_size_gb=1.0,
        tasks=(TaskSpec(10.0, 0.1),),
    )


def constellation() -> Constellation:
    sat = Satellite("A", 100.0, 1.0, WindowSet())
    gs_window = WindowedAvailability(WindowSet([Window(100.0, 300.0)]))
    return Constellation(
        [Plane(1, (sat,), com="A")],
        GroundStation("GS"),
        [Link("A", "GS", 1.0, 0.015, gs_window)],
    )


EPOCH = Epoch(index=0, start_s=50.0, ready_s=100.0)


def test_no_request_means_no_call() -> None:
    planner = ScriptedPlanner()
    rolling = RollingPlanner(planner, constellation())
    assert rolling.plan_epoch(EPOCH) is None
    assert planner.calls == []


def test_requests_are_released_no_earlier_than_the_epoch() -> None:
    planner = ScriptedPlanner(accept={"R1"})
    rolling = RollingPlanner(planner, constellation())
    rolling.plan_epoch(
        EPOCH, [request("R1", release_s=10.0), request("R2", release_s=70.0)]
    )
    released = {r.id: r.release_s for r in planner.calls[0].new_requests}
    assert released == {"R1": 50.0, "R2": 70.0}


def test_accepted_requests_are_committed_and_rejected_ones_leave_the_queue() -> None:
    planner = ScriptedPlanner(accept={"R1"})
    rolling = RollingPlanner(planner, constellation())
    rolling.plan_epoch(EPOCH, [request("R1"), request("R2")])
    assert [c.request.id for c in rolling.commitments] == ["R1"]
    assert rolling.pending == ()


def test_a_planner_failure_keeps_the_requests_pending() -> None:
    planner = ScriptedPlanner(fail=True)
    rolling = RollingPlanner(planner, constellation())
    assert rolling.plan_epoch(EPOCH, [request("R1")]) is None
    assert [r.id for r in rolling.pending] == ["R1"]
    assert rolling.commitments == ()


def test_a_request_the_planner_does_not_decide_stays_pending() -> None:
    class Silent(ScriptedPlanner):
        def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
            return PlanningDecision(plan=EpochPlan())

    rolling = RollingPlanner(Silent(), constellation())
    rolling.plan_epoch(EPOCH, [request("R1")])
    assert [r.id for r in rolling.pending] == ["R1"]


def test_commitments_are_passed_to_the_next_epoch() -> None:
    planner = ScriptedPlanner(accept={"R1"})
    rolling = RollingPlanner(planner, constellation())
    rolling.plan_epoch(EPOCH, [request("R1")])
    rolling.plan_epoch(Epoch(1, 200.0, 250.0), [request("R2")])
    second = planner.calls[1]
    assert [c.request.id for c in second.commitments] == ["R1"]
    assert [r.id for r in second.new_requests] == ["R2"]


def test_delivery_and_failure_release_the_commitment() -> None:
    planner = ScriptedPlanner(accept={"R1", "R2"})
    rolling = RollingPlanner(planner, constellation())
    rolling.plan_epoch(EPOCH, [request("R1"), request("R2")])
    rolling.on_delivered("R1")
    rolling.on_failed("R2")
    assert rolling.commitments == ()


def test_releasing_an_unknown_commitment_is_a_defect() -> None:
    with pytest.raises(StateError):
        RollingPlanner(ScriptedPlanner(), constellation()).on_delivered("R9")


def test_accepting_a_request_that_was_not_asked_is_a_planner_error() -> None:
    class Invented(ScriptedPlanner):
        def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
            ghost = PlannedTask("GHOST", 0, "A", 1.0, 2.0)
            return PlanningDecision(plan=EpochPlan(tasks=(ghost,)))

    rolling = RollingPlanner(Invented(), constellation())
    with pytest.raises(PlannerError, match="GHOST"):
        rolling.plan_epoch(EPOCH, [request("R1")])
