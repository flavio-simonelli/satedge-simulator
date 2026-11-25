"""Use of the HPCs and of the arcs: time held, over the time they were available."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from satedge_simulator.domain.topology import (
    Constellation,
    NodeId,
    WindowedAvailability,
)
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import (
    TaskEnded,
    TaskStarted,
    TransferEnded,
    TransferStarted,
)

Arc = tuple[NodeId, NodeId]


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """How much a resource was held, over the time it was available until the end.

    Attributes:
        busy_s: Seconds the resource was held, by tasks or transmissions, completed or not.
        available_s: Seconds of computing windows for an HPC, of visibility windows for a
            windowed arc, the whole simulation for an arc always available.
    """

    busy_s: float
    available_s: float

    @property
    def utilization(self) -> float | None:
        """``busy_s / available_s``, or ``None`` if the resource was never available."""
        return self.busy_s / self.available_s if self.available_s > 0 else None


class ResourceCollector:
    """Measures the time each HPC and each arc is held, from the notifications of the runtime.

    The definition is the one of the analysis of the scheduler, so the two can be compared. A
    resource still held at the end counts until the end.
    """

    def __init__(self, constellation: Constellation) -> None:
        self._constellation = constellation
        self._hpc_since: dict[tuple[str, int, NodeId], float] = {}
        self._arc_since: dict[tuple[str, int, NodeId, NodeId], float] = {}
        self._hpc_busy: dict[NodeId, float] = {}
        self._arc_busy: dict[Arc, float] = {}

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(TaskStarted, self._task_started)
        bus.subscribe(TaskEnded, self._task_ended)
        bus.subscribe(TransferStarted, self._transfer_started)
        bus.subscribe(TransferEnded, self._transfer_ended)

    def hpcs(self, end_s: float) -> Mapping[NodeId, ResourceUsage]:
        """The use of the HPC of each satellite, until ``end_s``."""
        busy = dict(self._hpc_busy)
        for (_, _, satellite), since in self._hpc_since.items():
            busy[satellite] = busy.get(satellite, 0.0) + max(0.0, end_s - since)
        return {
            s.id: ResourceUsage(
                busy.get(s.id, 0.0), s.hpc_windows.total_duration(end_s)
            )
            for s in self._constellation.satellites
        }

    def arcs(self, end_s: float) -> Mapping[Arc, ResourceUsage]:
        """The use of each direction of each link, until ``end_s``."""
        busy = dict(self._arc_busy)
        for (_, _, source, target), since in self._arc_since.items():
            busy[(source, target)] = busy.get((source, target), 0.0) + max(
                0.0, end_s - since
            )
        usage: dict[Arc, ResourceUsage] = {}
        for link in self._constellation.links:
            availability = link.availability
            available = (
                availability.windows.total_duration(end_s)
                if isinstance(availability, WindowedAvailability)
                else end_s
            )
            for arc in ((link.a, link.b), (link.b, link.a)):
                usage[arc] = ResourceUsage(busy.get(arc, 0.0), available)
        return usage

    def _task_started(self, n: TaskStarted) -> None:
        self._hpc_since[(n.request_id, n.task_index, n.satellite)] = n.time

    def _task_ended(self, n: TaskEnded) -> None:
        since = self._hpc_since.pop((n.request_id, n.task_index, n.satellite))
        self._hpc_busy[n.satellite] = self._hpc_busy.get(n.satellite, 0.0) + (
            n.time - since
        )

    def _transfer_started(self, n: TransferStarted) -> None:
        self._arc_since[(n.request_id, n.data_index, n.source, n.target)] = n.time

    def _transfer_ended(self, n: TransferEnded) -> None:
        since = self._arc_since.pop((n.request_id, n.data_index, n.source, n.target))
        arc = (n.source, n.target)
        self._arc_busy[arc] = self._arc_busy.get(arc, 0.0) + (n.time - since)
