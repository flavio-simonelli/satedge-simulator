"""Tests of the ground segment at run time, with a planner that decides what it is told.

The constellation is one satellite, A, with a contact to the ground station in [100, 300] and in
[1000, 1200]; with 50 s of lead time the epochs start at 50 s and 950 s. The plan reaches A
0.015 s after the contact opens. R1 has its raw data (4 Gb) on A from 20 s and one task that
lasts 4 + 8 + 1 = 13 s on the HPC.
"""

from collections.abc import Generator, Mapping
from dataclasses import dataclass, field

import pytest
import simpy

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.lifecycle import RequestStatus
from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.domain.topology import (
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.domain.violations import ViolationKind
from satedge_simulator.domain.workload import Priority, RequestSpec, TaskSpec
from satedge_simulator.errors import PlannerError
from satedge_simulator.planning.epochs import planning_epochs
from satedge_simulator.planning.ports import PlanningDecision, PlanningSnapshot
from satedge_simulator.planning.rolling_planner import RollingPlanner
from satedge_simulator.runtime.ground import GroundRuntime
from satedge_simulator.runtime.installer import PlanInstaller
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.network import NetworkRuntime

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
    request_id: str = "R1", arrival_s: float = 10.0, release_s: float = 20.0
) -> RequestSpec:
    return RequestSpec(
        id=request_id,
        priority=Priority.URGENT,
        origin="A",
        arrival_s=arrival_s,
        release_s=release_s,
        deadline_s=2000.0,
        raw_size_gb=4.0,
        tasks=(TaskSpec(execution_s=8.0, output_size_gb=1.0),),
    )


def constellation() -> Constellation:
    sat = Satellite("A", 100.0, 1.0, WindowSet([Window(0.0, 2000.0)]))
    contacts = WindowedAvailability(
        WindowSet([Window(100.0, 300.0), Window(1000.0, 1200.0)])
    )
    return Constellation(
        [Plane(1, (sat,), com="A")],
        GroundStation("GS"),
        [Link("A", "GS", 1.0, 0.015, contacts)],
    )


@dataclass
class Harness:
    env: simpy.Environment
    network: NetworkRuntime
    ledger: DataLedger
    rolling: RollingPlanner
    ground: GroundRuntime

    def plmm_at(self, *instants: float) -> dict[float, float]:
        levels: dict[float, float] = {}
        plmm = self.network.satellite("A").plmm

        def probe(instant: float) -> Generator[simpy.Event, object]:
            yield self.env.timeout(instant)
            levels[instant] = plmm.level_gb

        for instant in instants:
            self.env.process(probe(instant))
        return levels


def harness(planner: ScriptedPlanner, *requests: RequestSpec) -> Harness:
    env = simpy.Environment()
    net = constellation()
    network = NetworkRuntime(env, net, EPS)
    ledger = DataLedger(env)
    rolling = RollingPlanner(planner, net)
    ground = GroundRuntime(
        env,
        requests,
        planning_epochs(net, lead_time_s=50.0, end_s=2000.0),
        rolling,
        network,
        ledger,
        PlanInstaller(env, network, ledger, EPS),
        EPS,
    )
    return Harness(env, network, ledger, rolling, ground)


def test_an_accepted_request_runs_its_plan_and_is_delivered() -> None:
    h = harness(ScriptedPlanner({"R1": actions(120.0, 150.0)}), request())
    h.env.run()
    assert h.ground.records["R1"].history == [
        (10.0, RequestStatus.ARRIVED),
        (10.0, RequestStatus.QUEUED),
        (50.0, RequestStatus.ACCEPTED),
        (pytest.approx(151.015), RequestStatus.DELIVERED_ON_TIME),
    ]
    assert h.rolling.commitments == ()
    assert h.network.satellite("A").plmm.level_gb == 0.0


def test_the_raw_data_occupy_the_plmm_from_their_release() -> None:
    # Released at 20 s, long before the acceptance (50 s) and the plan (100.015 s); the task
    # writes its output from 132 s and frees them at its end, 133 s.
    h = harness(ScriptedPlanner({"R1": actions(120.0, 150.0)}), request())
    levels = h.plmm_at(19.0, 21.0, 132.5, 140.0)
    h.env.run()
    assert levels == {19.0: 0.0, 21.0: 4.0, 132.5: 5.0, 140.0: 1.0}


def test_a_rejected_request_frees_its_raw_data() -> None:
    h = harness(ScriptedPlanner(), request())
    levels = h.plmm_at(49.0, 51.0)
    h.env.run()
    assert h.ground.records["R1"].status is RequestStatus.REJECTED
    assert h.ground.records["R1"].history[-1] == (50.0, RequestStatus.REJECTED)
    assert levels == {49.0: 4.0, 51.0: 0.0}


def test_raw_data_released_after_the_rejection_are_not_stored() -> None:
    h = harness(ScriptedPlanner(), request(release_s=500.0))
    h.env.run()
    assert h.network.satellite("A").plmm.level_gb == 0.0
    assert not h.ledger.is_complete(DataKey("R1", 0, "A"))


def test_an_action_planned_before_the_plan_arrives_is_a_violation() -> None:
    # The plan reaches A at 100.015 s, but the task is planned at 90 s.
    h = harness(ScriptedPlanner({"R1": actions(90.0, 150.0)}), request())
    h.env.run()
    runtime = h.ground.runtimes["R1"]
    assert h.ground.records["R1"].status is RequestStatus.FAILED
    assert [(v.kind, v.node, v.at_s) for v in runtime.violations] == [
        (ViolationKind.PLAN_NOT_ARRIVED, "A", 90.0)
    ]
    assert h.rolling.commitments == ()
    assert h.network.satellite("A").plmm.level_gb == 0.0


def test_a_request_arriving_at_the_start_of_an_epoch_is_planned_in_it() -> None:
    planner = ScriptedPlanner({"R1": actions(120.0, 150.0)})
    h = harness(planner, request(arrival_s=50.0))
    h.env.run()
    assert [r.id for r in planner.calls[0].new_requests] == ["R1"]
    assert (50.0, RequestStatus.ACCEPTED) in h.ground.records["R1"].history


def test_a_request_arriving_after_the_planning_starts_waits_for_the_next_epoch() -> (
    None
):
    planner = ScriptedPlanner({"R1": actions(1020.0, 1050.0)})
    h = harness(planner, request(arrival_s=60.0))
    h.env.run()
    assert len(planner.calls) == 1  # the first epoch has nothing to decide
    assert (950.0, RequestStatus.ACCEPTED) in h.ground.records["R1"].history
    assert h.ground.records["R1"].status is RequestStatus.DELIVERED_ON_TIME


def test_a_failed_planner_leaves_the_requests_queued() -> None:
    h = harness(ScriptedPlanner(fail=True), request())
    h.env.run()
    assert h.ground.records["R1"].status is RequestStatus.QUEUED
    assert h.network.satellite("A").plmm.level_gb == 4.0  # the raw data stay acquired


def test_raw_data_that_do_not_fit_in_the_plmm_are_lost() -> None:
    h = harness(ScriptedPlanner({"R1": actions(120.0, 150.0)}), request())
    plmm = h.network.satellite("A").plmm

    def fill() -> Generator[simpy.Event, object]:
        yield from plmm.reserve(h.env, DataKey("X", 0, "A"), 98.0, EPS)

    h.env.process(fill())
    h.env.run()
    assert h.ground.lost_raw == ("R1",)
    runtime = h.ground.runtimes["R1"]
    assert [v.kind for v in runtime.violations] == [ViolationKind.DATA_NOT_READY]
