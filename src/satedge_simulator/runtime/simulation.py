"""The simulation: the composition root that builds the run-time objects and runs them."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import simpy

from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.domain.violations import Violation
from satedge_simulator.errors import PlanExecutionError, ScenarioError, StateError
from satedge_simulator.metrics.as_run import AsRun, AsRunCollector
from satedge_simulator.metrics.epochs import EpochCollector
from satedge_simulator.metrics.plmm import PlmmCollector
from satedge_simulator.metrics.resources import ResourceCollector
from satedge_simulator.metrics.summary import SimulationMetrics, summarize
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.planning.epochs import Epoch, planning_epochs
from satedge_simulator.planning.ports import Planner, PlanningDecision
from satedge_simulator.planning.rolling_planner import RollingPlanner
from satedge_simulator.runtime.ground import GroundRuntime
from satedge_simulator.runtime.installer import PlanInstaller
from satedge_simulator.runtime.ledger import DataLedger
from satedge_simulator.runtime.network import NetworkRuntime
from satedge_simulator.texts import VIOLATIONS


@dataclass(frozen=True, slots=True)
class SimulationOutcome:
    """What happened in a simulation.

    Attributes:
        end_s: Instant the simulation stopped, in seconds.
        records: The record of each request that arrived before the end, by identifier. Every
            record is final: a request still open at the end is ``UNFINISHED``.
        violations: The violations of the plan, in the order they happened.
        lost_raw: Requests whose raw data did not fit in the PLMM of their origin.
        decisions: The decision of each epoch in which the planner decided, in order.
        as_run: The executions completed, with their actual instants.
        metrics: The indicators of the simulation.
    """

    end_s: float
    records: Mapping[str, RequestRecord]
    violations: tuple[Violation, ...]
    lost_raw: tuple[str, ...]
    decisions: tuple[tuple[Epoch, PlanningDecision], ...]
    as_run: AsRun
    metrics: SimulationMetrics


class Simulation:
    """Builds the run-time objects of a scenario, injects their dependencies, and runs them.

    It is the only place that knows how the pieces fit: the network, the ledger of the data, the
    installer of the plans, the rolling planner around the planner, the ground segment, and the
    collectors of the metrics on the bus of the notifications.

    Args:
        scenario: What to simulate.
        planner: The planner that decides each epoch.
        lead_time_s: Seconds the planner has before each contact. ``None`` takes the lead time of
            the scenario.
        bus: The bus of the notifications, for subscribers of the caller such as the event log.
            ``None`` creates one.

    Raises:
        ScenarioError: If neither the scenario nor the caller gives the lead time.
    """

    def __init__(
        self,
        scenario: Scenario,
        planner: Planner,
        lead_time_s: float | None = None,
        bus: EventBus | None = None,
    ) -> None:
        lead = lead_time_s if lead_time_s is not None else scenario.lead_time_s
        if lead is None:
            raise ScenarioError(
                "lo scenario non indica l'anticipo del calcolo del planner"
            )
        self._scenario = scenario
        settings = scenario.settings
        tolerance = settings.tolerance_s
        self._end_s = settings.end_s
        self._env = simpy.Environment()
        bus = bus or EventBus()
        self._resources = ResourceCollector(scenario.constellation)
        self._plmms = PlmmCollector(scenario.constellation)
        self._epochs = EpochCollector()
        self._as_run = AsRunCollector()
        for collector in (self._resources, self._plmms, self._epochs, self._as_run):
            collector.attach(bus)
        network = NetworkRuntime(self._env, scenario.constellation, tolerance, bus)
        ledger = DataLedger(self._env)
        self._ground = GroundRuntime(
            self._env,
            scenario.requests,
            planning_epochs(scenario.constellation, lead, settings.end_s),
            RollingPlanner(planner, scenario.constellation),
            network,
            ledger,
            PlanInstaller(self._env, network, ledger, tolerance, bus),
            tolerance,
            on_violation=_stop if settings.strict else _go_on,
            bus=bus,
        )
        self._ran = False

    def run(self) -> SimulationOutcome:
        """Run the simulation up to its end, once.

        Raises:
            PlanExecutionError: In strict mode, at the first violation of the plan.
            StateError: If the simulation already ran.
        """
        if self._ran:
            raise StateError("la simulazione è già stata eseguita")
        self._ran = True
        self._env.run(until=self._end_s)
        records = self._ground.records
        for record in records.values():
            if not record.is_final:
                record.move(RequestStatus.UNFINISHED, self._end_s)
        violations = tuple(
            sorted(
                (v for r in self._ground.runtimes.values() for v in r.violations),
                key=lambda v: v.at_s,
            )
        )
        decisions = self._ground.decisions
        as_run = self._as_run.as_run()
        lost_raw = self._ground.lost_raw
        metrics = summarize(
            self._end_s,
            self._scenario.requests,
            records,
            violations,
            (decision.plan for _, decision in decisions),
            as_run,
            self._resources,
            self._plmms,
            self._epochs,
            len(lost_raw),
        )
        return SimulationOutcome(
            end_s=self._end_s,
            records=MappingProxyType(dict(records)),
            violations=violations,
            lost_raw=lost_raw,
            decisions=decisions,
            as_run=as_run,
            metrics=metrics,
        )


def _stop(violation: Violation) -> None:
    raise PlanExecutionError(
        f"violazione del piano ({VIOLATIONS[violation.kind]}) per la richiesta "
        f"{violation.request_id} su {violation.node} a {violation.at_s} s"
    )


def _go_on(violation: Violation) -> None:
    del violation
