"""Tests of the ground segment at run time, on the scenario of ``one_satellite``."""

from collections.abc import Generator
from dataclasses import dataclass

import pytest
import simpy
from one_satellite import (
    EPS,
    LEAD_TIME_S,
    ScriptedPlanner,
    actions,
    constellation,
    request,
)

from satedge_simulator.domain.lifecycle import RequestStatus
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.violations import ViolationKind
from satedge_simulator.planning.epochs import planning_epochs
from satedge_simulator.planning.rolling_planner import RollingPlanner
from satedge_simulator.runtime.ground import GroundRuntime
from satedge_simulator.runtime.installer import PlanInstaller
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.network import NetworkRuntime


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
        planning_epochs(net, lead_time_s=LEAD_TIME_S, end_s=2000.0),
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
