"""A scenario with one satellite and a planner that decides what it is told, for the run-time tests.

The constellation is one satellite, A, with a contact to the ground station in [100, 300] and in
[1000, 1200]; with 50 s of lead time the epochs start at 50 s and 950 s. The plan reaches A
0.015 s after the contact opens. R1 has its raw data (4 Gb) on A from 20 s and one task that
lasts 4 + 8 + 1 = 13 s on the HPC; its output (1 Gb) reaches the ground 1.015 s after it is sent.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.topology import (
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.errors import PlannerError
from satedge_simulator.planning.ports import PlanningDecision, PlanningSnapshot

LEAD_TIME_S = 50.0

SAT_A = Satellite("A", 100.0, 1.0, WindowSet([Window(0.0, 2000.0)]))

EPS = 1e-4
Actions = tuple[tuple[PlannedTask, ...], tuple[PlannedTransfer, ...]]


def actions(task_at: float, downlink_at: float, request_id: str = "R1") -> Actions:
    return (
        (PlannedTask(request_id, 0, "A", start_s=task_at, end_s=task_at + 13.0),),
        (
            PlannedTransfer(
                request_id, 1, "A", "GS", start_s=downlink_at, end_s=downlink_at + 1.0
            ),
        ),
    )


@dataclass
class ScriptedPlanner:
    """Accepts the requests it has actions for, with those actions; rejects the others."""

    plans: Mapping[str, Actions] = field(default_factory=dict)
    fail: bool = False
    calls: list[PlanningSnapshot] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "scripted"

    def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
        self.calls.append(snapshot)
        if self.fail:
            raise PlannerError("no solution in time")
        accepted = [r.id for r in snapshot.new_requests if r.id in self.plans]
        return PlanningDecision(
            plan=EpochPlan(
                tasks=tuple(t for r in accepted for t in self.plans[r][0]),
                transfers=tuple(t for r in accepted for t in self.plans[r][1]),
            ),
            rejected={
                r.id: "not scheduled"
                for r in snapshot.new_requests
                if r.id not in self.plans
            },
        )


def request(
    request_id: str = "R1", arrival_s: float = 10.0, release_s: float | None = None
) -> RequestSpec:
    # The release comes 20 s after the arrival, or at the arrival if that is later; the deadline
    # is 2000 s, or the release if that is later.
    release = max(20.0, arrival_s) if release_s is None else release_s
    return RequestSpec(
        id=request_id,
        priority=Priority.URGENT,
        origin=SAT_A,
        arrival_s=arrival_s,
        release_s=release,
        deadline_s=max(2000.0, release),
        raw_size_gb=4.0,
        tasks=(TaskSpec(execution_s=8.0, output_size_gb=1.0),),
    )


def constellation() -> Constellation:
    sat = SAT_A
    contacts = WindowedAvailability(
        WindowSet([Window(100.0, 300.0), Window(1000.0, 1200.0)])
    )
    return Constellation(
        [Plane(1, (sat,), com="A")],
        GroundStation("GS"),
        [Link("A", "GS", 1.0, 0.015, contacts)],
    )
