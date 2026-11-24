"""Scenario: what to simulate, and how long, with the planner's computing budget."""

from __future__ import annotations

import math
from dataclasses import dataclass

from satedge_simulator.domain.topology import Constellation
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.errors import ScenarioError


@dataclass(frozen=True, slots=True)
class SimulationSettings:
    """How the execution is run.

    Attributes:
        end_s: Instant at which the simulation stops, in seconds.
        tolerance_s: How long an action may wait for its preconditions past its planned instant.
        strict: Whether the first violation of the plan stops the simulation.
    """

    end_s: float
    tolerance_s: float = 1e-4
    strict: bool = False

    def __post_init__(self) -> None:
        if not (math.isfinite(self.end_s) and self.end_s > 0):
            raise ScenarioError(
                f"simulation end must be finite and > 0, got {self.end_s}"
            )
        if not (math.isfinite(self.tolerance_s) and self.tolerance_s >= 0):
            raise ScenarioError(
                f"tolerance must be finite and >= 0, got {self.tolerance_s}"
            )


@dataclass(frozen=True, slots=True)
class Scenario:
    """A complete simulation: the constellation, the workload and the settings.

    Attributes:
        constellation: The network that is simulated.
        requests: The requests that arrive during the simulation.
        settings: How the execution is run.
        lead_time_s: Seconds the planner has to compute a plan, before the contact with a COM.
            ``None`` means the time limit of the solver is used.
    """

    constellation: Constellation
    requests: tuple[RequestSpec, ...]
    settings: SimulationSettings
    lead_time_s: float | None = None

    def __post_init__(self) -> None:
        for request in self.requests:
            if not self.constellation.is_satellite(request.origin):
                raise ScenarioError(
                    f"request {request.id}: origin {request.origin!r} is not a satellite"
                )
        if self.lead_time_s is not None and not (
            math.isfinite(self.lead_time_s) and self.lead_time_s > 0
        ):
            raise ScenarioError(
                f"lead time must be finite and > 0, got {self.lead_time_s}"
            )
