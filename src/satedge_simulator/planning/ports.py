"""Port of the planner: the contract between the ground segment and whatever computes the plan.

The ground segment hands over a snapshot of one epoch and receives a decision. The simulator
depends only on these types; the scheduler is one implementation, behind an adapter.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.topology import Constellation, NodeId
from satedge_simulator.errors import PlannerError
from satedge_simulator.planning.epochs import Epoch


@dataclass(frozen=True, slots=True)
class Commitment:
    """A request already accepted in an earlier epoch and not yet delivered.

    Its actions are fixed: the planner must keep them and must not overlap new actions with them.

    Attributes:
        request: The request, in the version that was accepted.
        tasks: Its executions already planned.
        transfers: Its transmissions already planned.
    """

    request: RequestSpec
    tasks: tuple[PlannedTask, ...] = ()
    transfers: tuple[PlannedTransfer, ...] = ()


@dataclass(frozen=True, slots=True)
class PlanningSnapshot:
    """Everything the planner needs to decide one epoch.

    Attributes:
        epoch: The epoch being decided.
        constellation: The network the plan travels through.
        new_requests: Requests not yet decided, in FIFO order within each priority class.
        commitments: Requests already accepted, whose actions are fixed.
        plan_arrival_s: Instant the new plan reaches each satellite, ``inf`` if never.
    """

    epoch: Epoch
    constellation: Constellation
    new_requests: tuple[RequestSpec, ...]
    commitments: tuple[Commitment, ...]
    plan_arrival_s: Mapping[NodeId, float]


@dataclass(frozen=True, slots=True)
class PlanningDecision:
    """What the planner decided for the new requests of an epoch.

    Attributes:
        plan: The actions of the accepted requests. It holds no action of the commitments.
        rejected: Reason of the rejection of each rejected request, by request identifier.
        solver_time_s: Seconds the planner spent, in the simulated clock budget.
    """

    plan: EpochPlan
    rejected: Mapping[str, str] = field(default_factory=dict)
    solver_time_s: float = 0.0

    def __post_init__(self) -> None:
        if not (math.isfinite(self.solver_time_s) and self.solver_time_s >= 0):
            raise PlannerError(
                f"il tempo del solver deve essere finito e >= 0, invece è {self.solver_time_s}"
            )
        accepted = {t.request_id for t in self.plan.tasks} | {
            t.request_id for t in self.plan.transfers
        }
        both = accepted & set(self.rejected)
        if both:
            raise PlannerError(f"richieste sia accettate sia rifiutate: {sorted(both)}")
        object.__setattr__(self, "rejected", MappingProxyType(dict(self.rejected)))


class Planner(Protocol):
    """Computes the decision of one epoch from its snapshot."""

    @property
    def name(self) -> str:
        """Human-readable name of the planner, for the logs and the results."""
        ...

    def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
        """Decide the new requests of ``snapshot``, keeping the commitments fixed.

        Raises:
            PlannerError: If the planner cannot produce a usable decision.
        """
        ...
