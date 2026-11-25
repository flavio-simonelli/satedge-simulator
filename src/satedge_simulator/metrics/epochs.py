"""Indicators of the planning epochs."""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import EpochPlanned


@dataclass(frozen=True, slots=True)
class EpochMetrics:
    """The epochs in which the planner was called.

    Attributes:
        epochs: Epochs with a decision.
        new: Requests the planner was asked to decide, summed over the epochs.
        accepted: Requests accepted, summed over the epochs.
        rejected: Requests rejected, summed over the epochs.
        solver_time: Seconds the planner spent in each epoch.
        overruns: Epochs whose planner took longer than the lead time.
        max_unreachable: Most satellites the plan could not reach in one epoch.
    """

    epochs: int
    new: int
    accepted: int
    rejected: int
    solver_time: Distribution
    overruns: int
    max_unreachable: int


class EpochCollector:
    """Keeps the decision of each epoch, from the notifications of the ground segment."""

    def __init__(self) -> None:
        self._planned: list[EpochPlanned] = []

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(EpochPlanned, self._planned.append)

    def metrics(self) -> EpochMetrics:
        planned = self._planned
        return EpochMetrics(
            epochs=len(planned),
            new=sum(e.new for e in planned),
            accepted=sum(e.accepted for e in planned),
            rejected=sum(e.rejected for e in planned),
            solver_time=Distribution.of(e.solver_time_s for e in planned),
            overruns=sum(1 for e in planned if e.solver_time_s > e.ready_s - e.time),
            max_unreachable=max((e.unreachable for e in planned), default=0),
        )
