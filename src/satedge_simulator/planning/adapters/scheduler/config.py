"""The planner described by a solver file of satedge-workflow-scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from satedge_workflow_scheduler.common.errors import SchedulerError
from satedge_workflow_scheduler.io.files import load_solver_config
from satedge_workflow_scheduler.scheduling.deadline import DeadlineMode
from satedge_workflow_scheduler.solvers.milp.config import MilpConfig

from satedge_simulator.errors import DocumentError
from satedge_simulator.planning.adapters.scheduler.planner import SchedulerPlanner


@dataclass(frozen=True, slots=True)
class ConfiguredPlanner:
    """A planner read from its solver file, with what the simulation needs to know of it.

    Attributes:
        planner: The planner, behind the port of the simulator.
        time_limit_s: The time limit of the solver, the default lead time of the planning.
            ``None`` if the solver has none, as the sequential heuristic.
        hard_deadlines: Whether the deadlines are hard, so a request may be rejected.
    """

    planner: SchedulerPlanner
    time_limit_s: float | None
    hard_deadlines: bool


def load_planner(solver_path: str | Path, horizon_s: float) -> ConfiguredPlanner:
    """The planner described by the solver file in ``solver_path``.

    Raises:
        DocumentError: If the file cannot be read or does not describe a valid solver.
    """
    try:
        config = load_solver_config(solver_path)
    except SchedulerError as error:
        raise DocumentError(f"file del solver non valido: {error}") from error
    time_limit = config.solve.time_limit if isinstance(config, MilpConfig) else None
    return ConfiguredPlanner(
        planner=SchedulerPlanner(config, horizon_s),
        time_limit_s=time_limit,
        hard_deadlines=config.deadline is DeadlineMode.HARD,
    )
