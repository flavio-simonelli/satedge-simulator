"""Tests of the adapter to satedge-workflow-scheduler, on the case study.

The translation is checked by the scheduler's own feasibility checker: a plan that the
simulator produces from the scheduler's solution must pass it.
"""

from pathlib import Path

from satedge_workflow_scheduler.api import solve
from satedge_workflow_scheduler.scheduling.deadline import DeadlineMode
from satedge_workflow_scheduler.scheduling.feasibility import check
from satedge_workflow_scheduler.solvers.sequential.config import SequentialConfig

from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.planning.adapters.scheduler.from_solution import to_decision
from satedge_simulator.planning.adapters.scheduler.planner import SchedulerPlanner
from satedge_simulator.planning.adapters.scheduler.to_instance import to_instance
from satedge_simulator.planning.epochs import Epoch
from satedge_simulator.planning.ports import PlanningSnapshot

EXAMPLE = Path(__file__).parents[3] / "examples" / "casostudio" / "scenario.yaml"


def case_study_snapshot() -> PlanningSnapshot:
    scenario = load_scenario(EXAMPLE).scenario
    satellites = scenario.constellation.satellites
    return PlanningSnapshot(
        epoch=Epoch(index=0, start_s=0.0, ready_s=0.0),
        constellation=scenario.constellation,
        new_requests=scenario.requests,
        commitments=(),
        plan_arrival_s={s.id: 0.0 for s in satellites},
    )


def test_the_instance_has_the_case_study_network() -> None:
    snapshot = case_study_snapshot()
    instance = to_instance(snapshot, horizon_s=28800.0)
    assert len(instance.network.satellite_ids) == 18
    # 18 intra-plane links become 36 arcs; the COM-COM link two; the two COM-ground links
    # only one arc each, towards the ground station.
    assert len(instance.network.arcs) == 40
    assert all(arc.source != "GS" for arc in instance.network.arcs)


def test_hpc_windows_are_translated_unchanged() -> None:
    snapshot = case_study_snapshot()
    instance = to_instance(snapshot, horizon_s=28800.0)
    ours = snapshot.constellation.satellite("COM1").hpc_windows.windows
    theirs = instance.network.satellite("COM1").hpc_windows.windows
    assert [(w.start, w.end) for w in theirs] == [(w.start, w.end) for w in ours]


def test_requests_keep_their_release_and_deadline() -> None:
    snapshot = case_study_snapshot()
    instance = to_instance(snapshot, horizon_s=28800.0)
    first = instance.requests[0]
    assert first.id == "R1"
    assert first.release == 0.0
    assert first.deadline == 7200.0


def test_the_sequential_plan_passes_the_schedulers_own_checker() -> None:
    snapshot = case_study_snapshot()
    instance = to_instance(snapshot, horizon_s=28800.0)
    result = solve(instance, SequentialConfig())
    assert check(instance, result.solution, DeadlineMode.HARD) == ()


def test_the_planner_decision_comes_from_the_scheduler_solution() -> None:
    snapshot = case_study_snapshot()
    instance = to_instance(snapshot, horizon_s=28800.0)
    solution = solve(instance, SequentialConfig()).solution
    decision = SchedulerPlanner(SequentialConfig(), horizon_s=28800.0).plan(snapshot)
    expected = to_decision(solution, snapshot, solver_time_s=0.0)

    assert decision.plan.tasks == expected.plan.tasks
    assert dict(decision.rejected) == dict(expected.rejected)
    accepted = {t.request_id for t in decision.plan.tasks}
    assert accepted, "the sequential heuristic should accept some request"
    assert accepted | set(decision.rejected) == {r.id for r in snapshot.new_requests}
