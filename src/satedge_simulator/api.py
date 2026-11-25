"""The facade of the simulator: run a scenario, from objects or from its files."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.errors import ScenarioError
from satedge_simulator.io.results import write_metrics
from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.event_log import JsonlEventLog
from satedge_simulator.planning.adapters.scheduler.config import load_planner
from satedge_simulator.planning.adapters.scheduler.verification import (
    AsRunFinding,
    verify_as_run,
)
from satedge_simulator.planning.ports import Planner
from satedge_simulator.runtime.simulation import Simulation, SimulationOutcome

EVENTS_FILE = "events.jsonl"
METRICS_FILE = "metrics.json"


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """A simulation planned by satedge-workflow-scheduler, and the check of what it delivered.

    Attributes:
        outcome: What happened, with the metrics.
        findings: The constraints of the final model that the delivered requests do not
            respect; empty if they respect them all.
    """

    outcome: SimulationOutcome
    findings: tuple[AsRunFinding, ...]

    @property
    def verified(self) -> bool:
        """Whether the delivered requests respect the final model."""
        return not self.findings


def simulate(
    scenario: Scenario,
    planner: Planner,
    lead_time_s: float | None = None,
    bus: EventBus | None = None,
) -> SimulationOutcome:
    """Run ``scenario`` with any planner behind the port.

    Raises:
        ScenarioError: If neither the scenario nor the caller gives the lead time.
        PlanExecutionError: In strict mode, at the first violation of the plan.
    """
    return Simulation(scenario, planner, lead_time_s, bus).run()


def simulate_file(
    path: str | Path, output: str | Path | None = None
) -> SimulationResult:
    """Run the scenario in ``path`` with the scheduler of its solver file, and check it.

    The lead time of the planning is the one of the scenario or, if it gives none, the time
    limit of the solver. With ``output``, the directory receives the event log
    (``events.jsonl``) and the results (``metrics.json``).

    Raises:
        DocumentError: If a file of the scenario or the solver file is not valid.
        ScenarioError: If no lead time is given and the solver has no time limit.
        PlanExecutionError: In strict mode, at the first violation of the plan.
    """
    loaded = load_scenario(path)
    scenario = loaded.scenario
    end_s = scenario.settings.end_s
    configured = load_planner(loaded.solver_path, horizon_s=end_s)
    lead = (
        scenario.lead_time_s
        if scenario.lead_time_s is not None
        else configured.time_limit_s
    )
    if lead is None:
        raise ScenarioError(
            f"{path}: the scenario gives no lead time and the solver has no time limit"
        )
    bus = EventBus()
    with ExitStack() as stack:
        if output is not None:
            directory = Path(output)
            directory.mkdir(parents=True, exist_ok=True)
            log = stack.enter_context(
                (directory / EVENTS_FILE).open("w", encoding="utf-8")
            )
            JsonlEventLog(log).attach(bus)
        outcome = simulate(scenario, configured.planner, lead, bus)
    findings = verify_as_run(
        scenario.constellation,
        scenario.requests,
        outcome.records,
        outcome.decisions,
        outcome.as_run,
        horizon_s=end_s,
        hard_deadlines=configured.hard_deadlines,
        tolerance_s=max(scenario.settings.tolerance_s, 1e-6),
    )
    if output is not None:
        write_metrics(
            Path(output) / METRICS_FILE,
            outcome.end_s,
            outcome.metrics,
            outcome.records,
            findings,
        )
    return SimulationResult(outcome, findings)
