"""Plan: the actions the satellites must carry out, with their instants, for one planning epoch."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import ScenarioError


@dataclass(frozen=True, slots=True)
class PlannedTask:
    """A task that a satellite must run on its HPC.

    Attributes:
        request_id: Request the task belongs to.
        task_index: Position of the task in the pipeline.
        satellite: Satellite that runs the task.
        start_s: Instant the HPC starts the task, in seconds.
        end_s: Instant the HPC is released, in seconds. It includes reading the input and
            writing the output.
    """

    request_id: str
    task_index: int
    satellite: NodeId
    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        _check_span(
            self.start_s, self.end_s, f"task {self.request_id}/{self.task_index}"
        )


@dataclass(frozen=True, slots=True)
class PlannedTransfer:
    """A data item that a node must send on one arc.

    Attributes:
        request_id: Request the data belongs to.
        data_index: 0 for the raw data, ``k`` for the output of task ``k - 1``.
        source: Node that sends the data.
        target: Node that receives it.
        start_s: Instant the transmission starts, in seconds.
        end_s: Instant the transmission ends on the sender, in seconds. The propagation
            latency of the arc comes after it.
    """

    request_id: str
    data_index: int
    source: NodeId
    target: NodeId
    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        _check_span(
            self.start_s,
            self.end_s,
            f"transfer {self.request_id}/{self.data_index} {self.source}->{self.target}",
        )


@dataclass(frozen=True, slots=True)
class EpochPlan:
    """The plan of one epoch, for the requests that the planner accepted in it.

    Attributes:
        tasks: The task executions.
        transfers: The data transmissions.
        plan_arrival_s: Instant the plan reaches each satellite, in seconds. ``math.inf``
            means the plan never reaches it.
    """

    tasks: tuple[PlannedTask, ...] = ()
    transfers: tuple[PlannedTransfer, ...] = ()
    plan_arrival_s: Mapping[NodeId, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        keys = [(t.request_id, t.task_index) for t in self.tasks]
        if len(set(keys)) != len(keys):
            raise ScenarioError(
                "a task of a request appears more than once in the plan"
            )
        for node, arrival in self.plan_arrival_s.items():
            if math.isnan(arrival) or arrival < 0:
                raise ScenarioError(
                    f"plan arrival at {node} must be >= 0 or inf, got {arrival}"
                )
        object.__setattr__(
            self, "plan_arrival_s", MappingProxyType(dict(self.plan_arrival_s))
        )

    def tasks_of(self, satellite: NodeId) -> tuple[PlannedTask, ...]:
        """The tasks that ``satellite`` runs, in start order."""
        return tuple(
            sorted(
                (t for t in self.tasks if t.satellite == satellite),
                key=lambda t: t.start_s,
            )
        )

    def transfers_from(self, node: NodeId) -> tuple[PlannedTransfer, ...]:
        """The transmissions that ``node`` starts, in start order."""
        return tuple(
            sorted(
                (t for t in self.transfers if t.source == node), key=lambda t: t.start_s
            )
        )


def _check_span(start: float, end: float, what: str) -> None:
    if not (math.isfinite(start) and math.isfinite(end)):
        raise ScenarioError(f"{what}: instants must be finite")
    if start < 0 or end <= start:
        raise ScenarioError(f"{what}: needs 0 <= start < end, got [{start}, {end}]")
