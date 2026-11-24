"""Translation of a solution of satedge-workflow-scheduler into the decision of the simulator."""

from __future__ import annotations

from satedge_workflow_scheduler.domain.solution import Solution

from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.planning.ports import PlanningDecision, PlanningSnapshot

UNSPECIFIED_REJECTION = "rejected by the scheduler"


def to_decision(
    solution: Solution, snapshot: PlanningSnapshot, solver_time_s: float
) -> PlanningDecision:
    """The decision on the new requests of ``snapshot``.

    The commitments are left out: they are fixed, and the planner must not decide them again.
    """
    new_ids = {r.id for r in snapshot.new_requests}
    tasks = tuple(
        PlannedTask(e.request_id, e.task_index, e.satellite, e.start, e.end)
        for e in solution.schedule.executions
        if e.request_id in new_ids
    )
    transfers = tuple(
        PlannedTransfer(t.request_id, t.data_index, t.source, t.target, t.start, t.end)
        for t in solution.schedule.transfers
        if t.request_id in new_ids
    )
    rejected = {
        o.request_id: o.rejection_reason or UNSPECIFIED_REJECTION
        for o in solution.outcomes
        if o.request_id in new_ids and not o.accepted
    }
    return PlanningDecision(
        plan=EpochPlan(tasks=tasks, transfers=transfers),
        rejected=rejected,
        solver_time_s=solver_time_s,
    )
