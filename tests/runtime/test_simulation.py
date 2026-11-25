"""Tests of the whole simulation on the scenario of ``one_satellite``."""

import pytest
from one_satellite import LEAD_TIME_S, ScriptedPlanner, actions, constellation, request

from satedge_simulator.domain.lifecycle import RequestStatus
from satedge_simulator.domain.scenario import Scenario, SimulationSettings
from satedge_simulator.domain.violations import ViolationKind
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.errors import PlanExecutionError, ScenarioError, StateError
from satedge_simulator.runtime.simulation import Simulation


def scenario(
    *requests: RequestSpec,
    end_s: float = 2000.0,
    strict: bool = False,
    lead_time_s: float | None = LEAD_TIME_S,
) -> Scenario:
    return Scenario(
        constellation(),
        requests,
        SimulationSettings(end_s=end_s, strict=strict),
        lead_time_s=lead_time_s,
    )


def test_a_planned_request_is_delivered() -> None:
    planner = ScriptedPlanner({"R1": actions(120.0, 150.0)})
    outcome = Simulation(scenario(request()), planner).run()
    assert outcome.records["R1"].status is RequestStatus.DELIVERED_ON_TIME
    assert outcome.violations == ()
    assert outcome.lost_raw == ()
    assert outcome.end_s == 2000.0


def test_the_requests_still_open_at_the_end_are_unfinished() -> None:
    # R1 is accepted but its output would reach the ground at 151.015 s; R2 arrives after the
    # last epoch that starts before the end, so it is never decided.
    planner = ScriptedPlanner({"R1": actions(120.0, 150.0)})
    sim = Simulation(
        scenario(request(), request("R2", arrival_s=130.0), end_s=140.0), planner
    )
    outcome = sim.run()
    assert outcome.records["R1"].status is RequestStatus.UNFINISHED
    assert outcome.records["R1"].history[-1] == (140.0, RequestStatus.UNFINISHED)
    assert outcome.records["R2"].status is RequestStatus.UNFINISHED


def test_a_request_arriving_after_the_end_has_no_record() -> None:
    sim = Simulation(scenario(request(arrival_s=3000.0)), ScriptedPlanner())
    assert "R1" not in sim.run().records


def test_a_violation_fails_only_its_request_by_default() -> None:
    planner = ScriptedPlanner(
        {"R1": actions(90.0, 150.0), "R2": actions(170.0, 200.0, request_id="R2")}
    )
    outcome = Simulation(scenario(request(), request("R2")), planner).run()
    assert outcome.records["R1"].status is RequestStatus.FAILED
    assert outcome.records["R2"].status is RequestStatus.DELIVERED_ON_TIME
    assert [(v.kind, v.request_id) for v in outcome.violations] == [
        (ViolationKind.PLAN_NOT_ARRIVED, "R1")
    ]


def test_a_violation_stops_a_strict_simulation() -> None:
    planner = ScriptedPlanner({"R1": actions(90.0, 150.0)})
    sim = Simulation(scenario(request(), strict=True), planner)
    with pytest.raises(PlanExecutionError, match="plan_not_arrived for request R1"):
        sim.run()


def test_the_lead_time_of_the_caller_wins_over_the_scenario() -> None:
    # With 950 s of lead time the first contact (100 s) has no epoch, and the only epoch starts
    # at 50 s for the second contact (1000 s).
    planner = ScriptedPlanner({"R1": actions(1020.0, 1050.0)})
    sim = Simulation(scenario(request(arrival_s=40.0)), planner, lead_time_s=950.0)
    outcome = sim.run()
    assert [(c.epoch.start_s, c.epoch.ready_s) for c in planner.calls] == [
        (50.0, 1000.0)
    ]
    assert outcome.records["R1"].status is RequestStatus.DELIVERED_ON_TIME


def test_the_lead_time_is_required() -> None:
    with pytest.raises(ScenarioError, match="lead time"):
        Simulation(scenario(request(), lead_time_s=None), ScriptedPlanner())


def test_a_simulation_runs_once() -> None:
    sim = Simulation(scenario(request()), ScriptedPlanner())
    sim.run()
    with pytest.raises(StateError, match="already ran"):
        sim.run()
