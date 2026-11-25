"""Tests of the cross-check of the as-run calendar, on the case study.

The scheduler plans the case study with its sequential heuristic, the simulator executes the
plans, and the scheduler's own feasibility checker reads what was delivered.
"""

from dataclasses import replace
from functools import cache
from pathlib import Path

from satedge_workflow_scheduler.solvers.sequential.config import SequentialConfig

from satedge_simulator.domain.lifecycle import RequestStatus
from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.metrics.as_run import AsRun
from satedge_simulator.planning.adapters.scheduler.planner import SchedulerPlanner
from satedge_simulator.planning.adapters.scheduler.verification import (
    AsRunFinding,
    verify_as_run,
)
from satedge_simulator.runtime.simulation import Simulation, SimulationOutcome

EXAMPLE = Path(__file__).parents[3] / "examples" / "casostudio" / "scenario.yaml"
HORIZON_S = 28800.0
LEAD_TIME_S = 60.0


@cache
def case_study() -> SimulationOutcome:
    scenario = load_scenario(EXAMPLE).scenario
    planner = SchedulerPlanner(SequentialConfig(), horizon_s=HORIZON_S)
    return Simulation(scenario, planner, lead_time_s=LEAD_TIME_S).run()


def verify(outcome: SimulationOutcome, as_run: AsRun) -> tuple[AsRunFinding, ...]:
    scenario = load_scenario(EXAMPLE).scenario
    return verify_as_run(
        scenario.constellation,
        scenario.requests,
        outcome.records,
        outcome.decisions,
        as_run,
        horizon_s=HORIZON_S,
    )


def test_the_case_study_delivers_requests_without_violations() -> None:
    outcome = case_study()
    statuses = [r.status for r in outcome.records.values()]
    assert RequestStatus.DELIVERED_ON_TIME in statuses
    assert outcome.violations == ()


def test_what_the_simulator_delivered_passes_the_schedulers_checker() -> None:
    outcome = case_study()
    assert verify(outcome, outcome.as_run) == ()


def test_the_check_finds_an_execution_moved_by_hand() -> None:
    outcome = case_study()
    first, *rest = outcome.as_run.tasks
    moved = replace(first, start_s=first.start_s + 1.0, end_s=first.end_s + 1.0)
    findings = verify(outcome, replace(outcome.as_run, tasks=(moved, *rest)))
    assert {(f.epoch, f.constraint[:3], f.request_id) for f in findings} == {
        (0, "(3)", first.request_id),  # the next task starts before this one ends
        (0, "(8)", first.request_id),  # and on the same HPC
    }
    assert len(findings) == 2  # reported once, not again in each later epoch
