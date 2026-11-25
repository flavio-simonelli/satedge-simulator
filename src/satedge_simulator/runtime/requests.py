"""Runtime of an accepted request: its live actions, its failure and its delivery."""

from __future__ import annotations

from collections.abc import Generator, Iterable
from typing import Protocol

import simpy

from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.domain.violations import Violation
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.errors import StateError
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.satellite import SatelliteRuntime

Action = Generator[simpy.Event, object, bool]
"""A planned action ready to run: the generator of ``run_task`` or ``run_transfer``."""


class OutcomeListener(Protocol):
    """Who must know when an accepted request is over: the ground segment keeps its commitment
    until then."""

    def on_delivered(self, request_id: str) -> None: ...

    def on_failed(self, request_id: str) -> None: ...


class RequestRuntime:
    """An accepted request during the simulation.

    The plan reaches each satellite at its own instant, so the actions of the request are started
    one satellite at a time, through ``run``. The first violation fails the request: its live
    actions are interrupted, its data leave every PLMM, and no further action starts. The ground
    segment then drops its commitment, so the PLMM must be free in reality too, as the next plan
    assumes.

    The request is delivered when its final output is complete on the ground station, which is
    the delivery instant of the MILP model. It is on time if that instant is not later than the
    deadline: the tolerance applies to the preconditions of the actions, not to the deadline.
    """

    def __init__(
        self,
        env: simpy.Environment,
        request: RequestSpec,
        record: RequestRecord,
        ledger: DataLedger,
        satellites: Iterable[SatelliteRuntime],
        ground: NodeId,
        listener: OutcomeListener,
    ) -> None:
        if record.status is not RequestStatus.ACCEPTED:
            raise StateError(
                f"request {request.id}: runtime needs an accepted request, got {record.status}"
            )
        self._env = env
        self._request = request
        self._record = record
        self._satellites = tuple(satellites)
        self._listener = listener
        self._actions: list[simpy.Process] = []
        self._violations: list[Violation] = []
        final_output = DataKey(request.id, len(request.tasks), ground)
        env.process(self._await_delivery(ledger.complete_event(final_output)))

    @property
    def request(self) -> RequestSpec:
        return self._request

    @property
    def is_over(self) -> bool:
        """Whether the request is delivered or failed."""
        return self._record.is_final

    @property
    def violations(self) -> tuple[Violation, ...]:
        """The violations reported by the actions of the request, in order."""
        return tuple(self._violations)

    def run(self, action: Action) -> bool:
        """Start ``action``, unless the request is already over.

        Returns:
            Whether the action started. An action of a request that is over is discarded.
        """
        if self.is_over:
            action.close()
            return False
        self._actions.append(self._env.process(self._interruptible(action)))
        return True

    def report(self, violation: Violation) -> None:
        """Record a violation of an action of the request, and fail the request."""
        self._violations.append(violation)
        self.fail()

    def fail(self) -> None:
        """Fail the request now, if it is not over yet.

        The live actions are interrupted, except the one that is running, which reported the
        violation and stops by itself. Their data leave the PLMMs only after the interruptions
        are handled at this same instant, so that no action stores an item afterwards.
        """
        if self.is_over:
            return
        self._record.move(RequestStatus.FAILED, self._env.now)
        running = self._env.active_process
        for action in self._actions:
            if action.is_alive and action is not running:
                action.interrupt("request failed")
        self._env.process(self._free_memory())
        self._listener.on_failed(self._request.id)

    def _interruptible(self, action: Action) -> Generator[simpy.Event, object]:
        """Run ``action``, absorbing the interruption that a failure of the request sends."""
        try:
            yield from action
        except simpy.Interrupt:
            pass

    def _free_memory(self) -> Generator[simpy.Event, object]:
        """Free the data of the request from every PLMM, after the interruptions of this instant.

        Interruptions are urgent events, so they are all handled before this zero-delay timeout.
        """
        yield self._env.timeout(0)
        for satellite in self._satellites:
            satellite.plmm.release_request(self._request.id)

    def _await_delivery(
        self, final_output: simpy.Event
    ) -> Generator[simpy.Event, object]:
        """Deliver the request when its final output is complete on the ground station."""
        yield final_output
        if self.is_over:
            return
        on_time = self._env.now <= self._request.deadline_s
        status = (
            RequestStatus.DELIVERED_ON_TIME if on_time else RequestStatus.DELIVERED_LATE
        )
        self._record.move(status, self._env.now)
        self._listener.on_delivered(self._request.id)
