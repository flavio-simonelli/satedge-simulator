"""Installation of the plan of an epoch: each satellite starts its actions when the plan arrives."""

from __future__ import annotations

from collections.abc import Callable, Generator, Mapping

import simpy

from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import PlanInstalled
from satedge_simulator.runtime.ledger import DataLedger
from satedge_simulator.runtime.network import NetworkRuntime
from satedge_simulator.runtime.requests import Action, RequestRuntime
from satedge_simulator.runtime.tasks import run_task
from satedge_simulator.runtime.transfers import run_transfer


class PlanInstaller:
    """Hands the actions of a plan to the requests, satellite by satellite.

    A satellite learns its part of the plan at the instant the plan reaches it, and only then can
    start its actions. An action planned before that instant cannot start: it is a violation at
    its planned start. Durations and sizes come from the request in the domain, so the plan
    decides only the starts and the routes.
    """

    def __init__(
        self,
        env: simpy.Environment,
        network: NetworkRuntime,
        ledger: DataLedger,
        tolerance_s: float,
        bus: EventBus | None = None,
    ) -> None:
        self._env = env
        self._network = network
        self._ledger = ledger
        self._tolerance_s = tolerance_s
        self._bus = bus or EventBus()

    def install(
        self,
        plan: EpochPlan,
        arrival_s: Mapping[NodeId, float],
        requests: Mapping[str, RequestRuntime],
        epoch: int = 0,
    ) -> None:
        """Start the actions of ``plan`` as the plan reaches their satellites.

        Args:
            plan: The plan of the epoch, for the requests just accepted.
            arrival_s: Instant the plan reaches each satellite, ``inf`` if never.
            requests: The runtime of each request just accepted.
            epoch: Index of the epoch, for the notification of the installation.
        """
        involved = {t.satellite for t in plan.tasks} | {
            t.source for t in plan.transfers
        }
        for satellite in sorted(involved):
            if arrival_s[satellite] != float("inf"):
                self._env.process(
                    self._announce(epoch, satellite, arrival_s[satellite])
                )
        for task in plan.tasks:
            request = requests[task.request_id]
            self._when_known(
                request,
                task.satellite,
                task.start_s,
                arrival_s[task.satellite],
                self._task_action(request, task),
            )
        for transfer in plan.transfers:
            request = requests[transfer.request_id]
            self._when_known(
                request,
                transfer.source,
                transfer.start_s,
                arrival_s[transfer.source],
                self._transfer_action(request, transfer),
            )

    def _when_known(
        self,
        request: RequestRuntime,
        node: NodeId,
        start_s: float,
        known_s: float,
        action: Callable[[], Action],
    ) -> None:
        """Start ``action`` when ``node`` knows the plan, or report that it cannot know in time."""
        if start_s + self._tolerance_s < known_s:
            self._env.process(self._not_arrived(request, node, start_s))
        else:
            self._env.process(self._start_at(request, known_s, action))

    def _start_at(
        self, request: RequestRuntime, at_s: float, action: Callable[[], Action]
    ) -> Generator[simpy.Event, object]:
        yield self._env.timeout(max(0.0, at_s - self._env.now))
        request.run(action())

    def _announce(
        self, epoch: int, satellite: NodeId, at_s: float
    ) -> Generator[simpy.Event, object]:
        yield self._env.timeout(max(0.0, at_s - self._env.now))
        self._bus.publish(PlanInstalled(self._env.now, epoch, satellite))

    def _not_arrived(
        self, request: RequestRuntime, node: NodeId, start_s: float
    ) -> Generator[simpy.Event, object]:
        yield self._env.timeout(max(0.0, start_s - self._env.now))
        if not request.is_over:
            request.report(
                Violation(
                    self._env.now,
                    ViolationKind.PLAN_NOT_ARRIVED,
                    request.request.id,
                    node,
                )
            )

    def _task_action(
        self, request: RequestRuntime, task: PlannedTask
    ) -> Callable[[], Action]:
        spec = request.request
        return lambda: run_task(
            self._env,
            task,
            self._network.satellite(task.satellite),
            self._ledger,
            request.report,
            self._tolerance_s,
            spec.tasks[task.task_index],
            spec.data_sizes_gb()[task.task_index],
        )

    def _transfer_action(
        self, request: RequestRuntime, transfer: PlannedTransfer
    ) -> Callable[[], Action]:
        spec = request.request
        return lambda: run_transfer(
            self._env,
            transfer,
            self._network.arc(transfer.source, transfer.target),
            self._network.satellite(transfer.source),
            self._network.receiver(transfer.target),
            self._ledger,
            request.report,
            self._tolerance_s,
            spec.data_sizes_gb()[transfer.data_index],
        )
