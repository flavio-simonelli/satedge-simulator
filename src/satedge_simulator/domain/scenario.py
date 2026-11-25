"""Scenario: what to simulate, and how long, with the planner's computing budget."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from satedge_simulator.domain.topology import Constellation
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.domain.workload_model import WorkloadModel
from satedge_simulator.errors import ScenarioError
from satedge_simulator.rng.rngs import DEFAULT_SEED, MODULUS


@dataclass(frozen=True, slots=True)
class SimulationSettings:
    """How the execution is run.

    Attributes:
        end_s: Instant at which the simulation stops, in seconds.
        tolerance_s: How long an action may wait for its preconditions past its planned instant.
        strict: Whether the first violation of the plan stops the simulation.
        seed: Initial state of the random number generator, ``0 < seed < 2³¹ − 1``. With the
            same seed, two runs draw the same workload.
    """

    end_s: float
    tolerance_s: float = 1e-4
    strict: bool = False
    seed: int = DEFAULT_SEED

    def __post_init__(self) -> None:
        if not (math.isfinite(self.end_s) and self.end_s > 0):
            raise ScenarioError(
                f"la fine della simulazione deve essere finita e > 0, invece è {self.end_s}"
            )
        if not 0 < self.seed < MODULUS:
            raise ScenarioError(
                f"il seed deve essere compreso tra 1 e {MODULUS - 1}, invece è {self.seed}"
            )
        if not (math.isfinite(self.tolerance_s) and self.tolerance_s >= 0):
            raise ScenarioError(
                f"la tolleranza deve essere finita e >= 0, invece è {self.tolerance_s}"
            )


def world_horizon_s(
    end_s: float, requests: Iterable[RequestSpec], model: WorkloadModel | None
) -> float:
    """How far the windows of the network must reach for a run that ends at ``end_s``.

    The observation stops at the end, but the constellation does not: a request that arrives
    near the end is planned against the windows after it, up to its deadline. So the computing
    windows, the periodic contacts and the horizon of the planner reach the latest deadline a
    request of the run can have: the deadline of a request of the workload file, or the end
    plus the longest life of a generated request. Without it, the requests near the end would
    be rejected only because the windows stop there, and the finite-horizon estimates would be
    biased.
    """
    horizon = max((r.deadline_s for r in requests), default=end_s)
    if model is not None:
        horizon = max(horizon, end_s + model.longest_life_s)
    return max(horizon, end_s)


@dataclass(frozen=True, slots=True)
class Scenario:
    """A complete simulation: the constellation, the workload and the settings.

    Attributes:
        constellation: The network that is simulated.
        requests: The requests that arrive during the simulation.
        settings: How the execution is run.
        lead_time_s: Seconds the planner has to compute a plan, before the contact with a COM.
            ``None`` means the time limit of the solver is used.
        workload_model: The stochastic workload, whose requests are drawn during the run, on
            top of ``requests``; ``None`` for a deterministic workload.
    """

    constellation: Constellation
    requests: tuple[RequestSpec, ...]
    settings: SimulationSettings
    lead_time_s: float | None = None
    workload_model: WorkloadModel | None = None

    def __post_init__(self) -> None:
        for request in self.requests:
            if not self.constellation.is_satellite(request.origin):
                raise ScenarioError(
                    f"richiesta {request.id}: l'origine {request.origin!r} non è un satellite"
                )
        if self.lead_time_s is not None and not (
            math.isfinite(self.lead_time_s) and self.lead_time_s > 0
        ):
            raise ScenarioError(
                f"l'anticipo del calcolo deve essere finito e > 0, invece è {self.lead_time_s}"
            )

    @property
    def world_horizon_s(self) -> float:
        """How far the windows of the network reach: see :func:`world_horizon_s`."""
        return world_horizon_s(self.settings.end_s, self.requests, self.workload_model)
