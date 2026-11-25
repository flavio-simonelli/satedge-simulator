"""The facade of the simulator: run a scenario, from objects or from its files."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from satedge_simulator.analysis.autocorrelation_study import (
    AutocorrelationReport,
    autocorrelation_study,
)
from satedge_simulator.analysis.batch_means import BatchMeansReport, batch_means
from satedge_simulator.analysis.replications import ReplicationReport, replicate
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.errors import ScenarioError
from satedge_simulator.io.analysis_results import (
    write_autocorrelation,
    write_batch_means,
    write_replications,
)
from satedge_simulator.io.results import write_metrics
from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.event_log import JsonlEventLog
from satedge_simulator.planning.adapters.scheduler.config import load_planner
from satedge_simulator.planning.adapters.scheduler.planner import SchedulerPlanner
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


@dataclass(frozen=True, slots=True)
class _Prepared:
    """A scenario read from its files, with its planner and the lead time of the planning."""

    scenario: Scenario
    planner: SchedulerPlanner
    lead_time_s: float
    hard_deadlines: bool


def _prepare(path: str | Path) -> _Prepared:
    """Read the scenario in ``path`` and its solver.

    The lead time of the planning is the one of the scenario or, if it gives none, the time
    limit of the solver. The planner sees the windows up to the horizon of the world, beyond
    the end of the run.

    Raises:
        DocumentError: If a file of the scenario or the solver file is not valid.
        ScenarioError: If no lead time is given and the solver has no time limit.
    """
    loaded = load_scenario(path)
    scenario = loaded.scenario
    configured = load_planner(loaded.solver_path, horizon_s=scenario.world_horizon_s)
    lead = (
        scenario.lead_time_s
        if scenario.lead_time_s is not None
        else configured.time_limit_s
    )
    if lead is None:
        raise ScenarioError(
            f"{path}: lo scenario non indica l'anticipo del calcolo e il solver non ha un "
            "limite di tempo"
        )
    return _Prepared(scenario, configured.planner, lead, configured.hard_deadlines)


def simulate_file(
    path: str | Path, output: str | Path | None = None
) -> SimulationResult:
    """Run the scenario in ``path`` with the scheduler of its solver file, and check it.

    With ``output``, the directory receives the event log (``events.jsonl``) and the results
    (``metrics.json``).

    Raises:
        DocumentError: If a file of the scenario or the solver file is not valid.
        ScenarioError: If no lead time is given and the solver has no time limit.
        PlanExecutionError: In strict mode, at the first violation of the plan.
    """
    prepared = _prepare(path)
    scenario = prepared.scenario
    bus = EventBus()
    with ExitStack() as stack:
        if output is not None:
            directory = Path(output)
            directory.mkdir(parents=True, exist_ok=True)
            log = stack.enter_context(
                (directory / EVENTS_FILE).open("w", encoding="utf-8")
            )
            JsonlEventLog(log).attach(bus)
        outcome = simulate(scenario, prepared.planner, prepared.lead_time_s, bus)
    findings = verify_as_run(
        scenario.constellation,
        outcome.requests,
        outcome.records,
        outcome.decisions,
        outcome.as_run,
        horizon_s=scenario.world_horizon_s,
        hard_deadlines=prepared.hard_deadlines,
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


def replicate_file(
    path: str | Path,
    replications: int,
    cell_s: float,
    welch_window: int,
    level: float = 0.95,
    output: str | Path | None = None,
) -> ReplicationReport:
    """Finite horizon: independent replications of the scenario in ``path``, and its transient.

    With ``output``, the directory receives ``replications.json`` and ``transient.csv``.
    """
    prepared = _prepare(path)
    report = replicate(
        prepared.scenario,
        prepared.planner,
        replications,
        cell_s,
        welch_window,
        level,
        prepared.lead_time_s,
    )
    if output is not None:
        write_replications(output, report)
    return report


def batch_means_file(
    path: str | Path,
    warmup_s: float,
    batch_size: int,
    batch_duration_s: float,
    level: float = 0.95,
    output: str | Path | None = None,
) -> BatchMeansReport:
    """Infinite horizon: batch means on one long run of the scenario in ``path``.

    With ``output``, the directory receives ``batch_means.json`` and ``batches.csv``.
    """
    prepared = _prepare(path)
    report = batch_means(
        prepared.scenario,
        prepared.planner,
        warmup_s,
        batch_size,
        batch_duration_s,
        level,
        prepared.lead_time_s,
    )
    if output is not None:
        write_batch_means(output, report)
    return report


def autocorrelation_file(
    path: str | Path, warmup_s: float, max_lag: int, output: str | Path | None = None
) -> AutocorrelationReport:
    """The autocorrelation of the per-request statistics of one long run of ``path``.

    With ``output``, the directory receives ``autocorrelation.json`` and ``autocorrelation.csv``.
    """
    prepared = _prepare(path)
    report = autocorrelation_study(
        prepared.scenario, prepared.planner, warmup_s, max_lag, prepared.lead_time_s
    )
    if output is not None:
        write_autocorrelation(output, report)
    return report
