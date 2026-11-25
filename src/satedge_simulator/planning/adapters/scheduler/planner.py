"""Planner backed by satedge-workflow-scheduler: the only object of the simulator that calls it."""

from __future__ import annotations

from satedge_workflow_scheduler.api import SolverConfig, solve
from satedge_workflow_scheduler.common.errors import SchedulerError
from satedge_workflow_scheduler.solvers.milp.strategy import BackendFactory

from satedge_simulator.errors import PlannerError
from satedge_simulator.planning.adapters.scheduler.from_solution import to_decision
from satedge_simulator.planning.adapters.scheduler.to_instance import to_instance
from satedge_simulator.planning.ports import PlanningDecision, PlanningSnapshot


class SchedulerPlanner:
    """Decides each epoch by solving its scheduling instance.

    Args:
        config: The solver configuration: the MILP or the sequential heuristic.
        horizon_s: The delivery horizon of the instances, in seconds.
        backend: The MILP backend. ``None`` uses the default, which needs Gurobi.
    """

    def __init__(
        self,
        config: SolverConfig,
        horizon_s: float,
        backend: BackendFactory | None = None,
    ) -> None:
        self._config = config
        self._horizon_s = horizon_s
        self._backend = backend

    @property
    def name(self) -> str:
        return "satedge-workflow-scheduler"

    def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
        """Solve the instance of ``snapshot``, and translate the solution back.

        Raises:
            PlannerError: If the scheduler fails, finds no solution, or rejects the instance.
        """
        instance = to_instance(snapshot, self._horizon_s)
        try:
            result = solve(instance, self._config, backend=self._backend)
        except SchedulerError as error:
            raise PlannerError(
                f"lo scheduler non ha prodotto un piano: {error}"
            ) from error
        solver_time = result.statistics.solver_time_s or 0.0
        return to_decision(result.solution, snapshot, solver_time)
