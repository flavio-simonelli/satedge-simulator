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
from satedge_simulator.planning.epochs import planning_epochs
from satedge_simulator.planning.ports import Planner
from satedge_simulator.planning.rolling_planner import RollingPlanner
from satedge_simulator.runtime.ground import GroundRuntime
from satedge_simulator.runtime.installer import PlanInstaller
from satedge_simulator.runtime.ledger import DataLedger
from satedge_simulator.runtime.network import NetworkRuntime


@dataclass(frozen=True, slots=True)
class SimulationOutcome:
    """What happened in a simulation.

    Attributes:
        end_s: Instant the simulation stopped, in seconds.
        records: The record of each request that arrived before the end, by identifier. Every
            record is final: a request still open at the end is ``UNFINISHED``.
        violations: The violations of the plan, in the order they happened.
        lost_raw: Requests whose raw data did not fit in the PLMM of their origin.
    """

    end_s: float
    records: Mapping[str, RequestRecord]
    violations: tuple[Violation, ...]
    lost_raw: tuple[str, ...]


class Simulation:
    """Builds the run-time objects of a scenario, injects their dependencies, and runs them.

    It is the only place that knows how the pieces fit: the network, the ledger of the data, the
    installer of the plans, the rolling planner around the planner, and the ground segment.

    Args:
        scenario: What to simulate.
        planner: The planner that decides each epoch.
        lead_time_s: Seconds the planner has before each contact. ``None`` takes the lead time of
            the scenario.

    Raises:
        ScenarioError: If neither the scenario nor the caller gives the lead time.
    """

    def __init__(
        self, scenario: Scenario, planner: Planner, lead_time_s: float | None = None
    ) -> None:
        lead = lead_time_s if lead_time_s is not None else scenario.lead_time_s
        if lead is None:
            raise ScenarioError(
                "the lead time of the planner is missing from the scenario"
            )
        settings = scenario.settings
        tolerance = settings.tolerance_s
        self._end_s = settings.end_s
        self._env = simpy.Environment()
        network = NetworkRuntime(self._env, scenario.constellation, tolerance)
        ledger = DataLedger(self._env)
        self._ground = GroundRuntime(
            self._env,
            scenario.requests,
            planning_epochs(scenario.constellation, lead, settings.end_s),
            RollingPlanner(planner, scenario.constellation),
            network,
            ledger,
            PlanInstaller(self._env, network, ledger, tolerance),
            tolerance,
            on_violation=_stop if settings.strict else _go_on,
        )
        self._ran = False

    def run(self) -> SimulationOutcome:
        """Run the simulation up to its end, once.

        Raises:
            PlanExecutionError: In strict mode, at the first violation of the plan.
            StateError: If the simulation already ran.
        """
        if self._ran:
            raise StateError("the simulation already ran")
        self._ran = True
        self._env.run(until=self._end_s)
        records = self._ground.records
        for record in records.values():
            if not record.is_final:
                record.move(RequestStatus.UNFINISHED, self._end_s)
        violations = sorted(
            (v for r in self._ground.runtimes.values() for v in r.violations),
            key=lambda v: v.at_s,
        )
        return SimulationOutcome(
            end_s=self._end_s,
            records=MappingProxyType(dict(records)),
            violations=tuple(violations),
            lost_raw=self._ground.lost_raw,
        )


def _stop(violation: Violation) -> None:
    raise PlanExecutionError(
        f"{violation.kind} for request {violation.request_id} on {violation.node} "
        f"at {violation.at_s} s"
    )


def _go_on(violation: Violation) -> None:
    del violation
