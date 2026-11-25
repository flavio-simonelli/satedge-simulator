"""The as-run calendar: what was executed, in the model of the simulator, against the plan."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass

from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import (
    TaskEnded,
    TaskStarted,
    TransferEnded,
    TransferStarted,
)

_TaskKey = tuple[str, int, NodeId]
_TransferKey = tuple[str, int, NodeId, NodeId]


@dataclass(frozen=True, slots=True)
class AsRun:
    """The executions completed during the simulation, with their actual instants.

    A task spans from the instant it took the HPC to the instant it released it; a transfer,
    from the instant it took the channel to the end of the transmission on the sender, as in
    the plan. The latency of the arc comes after.
    """

    tasks: tuple[PlannedTask, ...] = ()
    transfers: tuple[PlannedTransfer, ...] = ()

    def of_requests(self, request_ids: Collection[str]) -> AsRun:
        """The part of the calendar that belongs to ``request_ids``."""
        return AsRun(
            tasks=tuple(t for t in self.tasks if t.request_id in request_ids),
            transfers=tuple(t for t in self.transfers if t.request_id in request_ids),
        )

    def deviation(self, plans: Iterable[EpochPlan]) -> Distribution:
        """How far each executed action started from its planned start, in seconds."""
        plans = tuple(plans)
        planned_tasks = {_task_key(t): t.start_s for p in plans for t in p.tasks}
        planned_transfers = {
            _transfer_key(x): x.start_s for p in plans for x in p.transfers
        }
        task_gaps = [
            abs(t.start_s - planned_tasks[_task_key(t)])
            for t in self.tasks
            if _task_key(t) in planned_tasks
        ]
        transfer_gaps = [
            abs(x.start_s - planned_transfers[_transfer_key(x)])
            for x in self.transfers
            if _transfer_key(x) in planned_transfers
        ]
        return Distribution.of(task_gaps + transfer_gaps)


def _task_key(task: PlannedTask) -> _TaskKey:
    return (task.request_id, task.task_index, task.satellite)


def _transfer_key(transfer: PlannedTransfer) -> _TransferKey:
    return (transfer.request_id, transfer.data_index, transfer.source, transfer.target)


class AsRunCollector:
    """Builds the as-run calendar from the notifications of the runtime."""

    def __init__(self) -> None:
        self._task_since: dict[_TaskKey, float] = {}
        self._transfer_since: dict[_TransferKey, float] = {}
        self._tasks: list[PlannedTask] = []
        self._transfers: list[PlannedTransfer] = []

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(TaskStarted, self._task_started)
        bus.subscribe(TaskEnded, self._task_ended)
        bus.subscribe(TransferStarted, self._transfer_started)
        bus.subscribe(TransferEnded, self._transfer_ended)

    def as_run(self) -> AsRun:
        return AsRun(tuple(self._tasks), tuple(self._transfers))

    def _task_started(self, n: TaskStarted) -> None:
        self._task_since[(n.request_id, n.task_index, n.satellite)] = n.time

    def _task_ended(self, n: TaskEnded) -> None:
        start = self._task_since.pop((n.request_id, n.task_index, n.satellite))
        if n.completed:
            self._tasks.append(
                PlannedTask(n.request_id, n.task_index, n.satellite, start, n.time)
            )

    def _transfer_started(self, n: TransferStarted) -> None:
        self._transfer_since[(n.request_id, n.data_index, n.source, n.target)] = n.time

    def _transfer_ended(self, n: TransferEnded) -> None:
        start = self._transfer_since.pop(
            (n.request_id, n.data_index, n.source, n.target)
        )
        if n.completed:
            self._transfers.append(
                PlannedTransfer(
                    n.request_id, n.data_index, n.source, n.target, start, n.time
                )
            )
