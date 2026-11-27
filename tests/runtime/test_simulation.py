"""Tests of the whole simulation on the scenario of ``one_satellite``."""

import pytest
from one_satellite import LEAD_TIME_S, ScriptedPlanner, actions, constellation, request

from satedge_simulator.domain.lifecycle import RequestStatus
from satedge_simulator.domain.plan import PlannedTask
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.scenario import Scenario, SimulationSettings
from satedge_simulator.domain.violations import ViolationKind
from satedge_simulator.errors import InputError, PlanExecutionError, StateError
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
    with pytest.raises(
        PlanExecutionError, match="piano non ancora arrivato.*richiesta R1"
    ):
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
    without_lead_time = scenario(request(), lead_time_s=None)
    planner = ScriptedPlanner()
    with pytest.raises(InputError, match="anticipo"):
        Simulation(without_lead_time, planner)


def test_a_simulation_runs_once() -> None:
    sim = Simulation(scenario(request()), ScriptedPlanner())
    sim.run()
    with pytest.raises(StateError, match="già stata eseguita"):
        sim.run()


def test_the_metrics_of_a_delivered_request_match_a_count_by_hand() -> None:
    # Raw data at 20 s, task 120-133 s on A, downlink 150-151 s, delivery at 151.015 s.
    planner = ScriptedPlanner({"R1": actions(120.0, 150.0)})
    outcome = Simulation(scenario(request()), planner).run()
    metrics = outcome.metrics
    urgent = metrics.requests[0]
    assert (urgent.arrived, urgent.accepted, urgent.delivered_on_time) == (1, 1, 1)
    assert urgent.response_from_release.max == pytest.approx(151.015 - 20.0)
    assert urgent.response_from_arrival.max == pytest.approx(151.015 - 10.0)
    assert urgent.tardiness.max == 0.0
    assert metrics.hpcs["A"].busy_s == pytest.approx(13.0)
    assert metrics.hpcs["A"].available_s == 2000.0
    assert metrics.arcs[("A", "GS")].busy_s == pytest.approx(1.0)
    assert metrics.arcs[("A", "GS")].available_s == 400.0  # [100, 300] and [1000, 1200]
    assert metrics.plmms["A"].peak_gb == 5.0
    # 4 Gb from 20 s to 132 s, 5 Gb to 133 s, 1 Gb to 151 s
    assert metrics.plmms["A"].mean_gb == pytest.approx(
        (4 * 112 + 5 * 1 + 1 * 18) / 2000
    )
    assert (metrics.epochs.epochs, metrics.epochs.accepted) == (1, 1)
    assert metrics.violations == {}
    assert metrics.deviation.max == 0.0  # deterministic: the plan is executed as it is
    assert outcome.as_run.tasks == (PlannedTask("R1", 0, "A", 120.0, 133.0),)


def test_the_violations_are_counted_by_kind() -> None:
    planner = ScriptedPlanner({"R1": actions(90.0, 150.0)})
    metrics = Simulation(scenario(request()), planner).run().metrics
    assert metrics.violations == {ViolationKind.PLAN_NOT_ARRIVED: 1}
    assert metrics.requests[0].failed == 1
