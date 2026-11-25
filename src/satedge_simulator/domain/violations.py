"""Violations: the moments when the execution cannot follow the plan."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import StateError


class ViolationKind(StrEnum):
    """Why an action of the plan could not start at its planned instant."""

    DATA_NOT_READY = "data_not_ready"
    HPC_BUSY = "hpc_busy"
    LINK_BUSY = "link_busy"
    PLMM_FULL = "plmm_full"
    HPC_WINDOW = "hpc_window"
    LINK_WINDOW = "link_window"
    PLAN_NOT_ARRIVED = "plan_not_arrived"


@dataclass(frozen=True, slots=True)
class Violation:
    """One action of the plan that could not be carried out as planned.

    Attributes:
        at_s: Instant the violation is detected, in seconds.
        kind: Reason of the violation.
        request_id: Request whose action failed.
        node: Node where the action was supposed to start.
    """

    at_s: float
    kind: ViolationKind
    request_id: str
    node: NodeId

    def __post_init__(self) -> None:
        if not (math.isfinite(self.at_s) and self.at_s >= 0):
            raise StateError(
                f"l'istante della violazione deve essere finito e >= 0, invece è {self.at_s}"
            )
