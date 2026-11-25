"""Runtime of the ground segment: arrivals, raw data, and the planning of each epoch."""

from __future__ import annotations

from collections.abc import Generator, Iterable, Mapping
from types import MappingProxyType

import simpy

from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.plan import EpochPlan
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.planning.epochs import Epoch
from satedge_simulator.planning.ports import PlanningDecision
from satedge_simulator.planning.propagation import plan_arrival_times
from satedge_simulator.planning.rolling_planner import RollingPlanner
from satedge_simulator.runtime.installer import PlanInstaller
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.network import NetworkRuntime
from satedge_simulator.runtime.requests import RequestRuntime


class GroundRuntime:
    """The processes of the ground segment, and the record of every request.

    - A request reaches the ground segment at its arrival and waits in the queue.
    - Its raw data occupy the PLMM of its origin from their release, whatever the decision on the
      request: the satellite has acquired them. They leave it when the request is rejected,
      fails, or is served by its first action. If the PLMM cannot hold them, they are lost.
    - At the start of each epoch the rolling planner decides the queued requests. The
      zero-delay wait before the snapshot lets the arrivals of that same instant enter it.
    - The plan of the accepted requests reaches each satellite at the instant computed from the
      network; their actions start from there.
    """

    def __init__(
        self,
        env: simpy.Environment,
        requests: Iterable[RequestSpec],
        epochs: Iterable[Epoch],
        rolling: RollingPlanner,
        network: NetworkRuntime,
        ledger: DataLedger,
        installer: PlanInstaller,
        tolerance_s: float,
    ) -> None:
        self._env = env
        self._rolling = rolling
        self._network = network
        self._ledger = ledger
        self._installer = installer
        self._tolerance_s = tolerance_s
        self._specs = {r.id: r for r in requests}
        self._records: dict[str, RequestRecord] = {}
        self._runtimes: dict[str, RequestRuntime] = {}
        self._arrived: list[RequestSpec] = []
        self._lost_raw: list[str] = []
        for spec in self._specs.values():
            env.process(self._arrive(spec))
            env.process(self._acquire_raw(spec))
        env.process(self._plan(tuple(epochs)))

    @property
    def records(self) -> Mapping[str, RequestRecord]:
        """The record of each request that has arrived, by identifier."""
        return MappingProxyType(self._records)

    @property
    def runtimes(self) -> Mapping[str, RequestRuntime]:
        """The runtime of each accepted request, by identifier."""
        return MappingProxyType(self._runtimes)

    @property
    def lost_raw(self) -> tuple[str, ...]:
        """Requests whose raw data did not fit in the PLMM of their origin at their release."""
        return tuple(self._lost_raw)

    def _arrive(self, spec: RequestSpec) -> Generator[simpy.Event, object]:
        yield self._env.timeout(spec.arrival_s)
        record = RequestRecord(
            spec.id, history=[(self._env.now, RequestStatus.ARRIVED)]
        )
        record.move(RequestStatus.QUEUED, self._env.now)
        self._records[spec.id] = record
        self._arrived.append(spec)

    def _acquire_raw(self, spec: RequestSpec) -> Generator[simpy.Event, object]:
        yield self._env.timeout(spec.release_s)
        record = self._records.get(spec.id)
        if record is not None and record.is_final:
            return  # already rejected or failed: nobody will use the raw data
        raw = DataKey(spec.id, 0, spec.origin)
        plmm = self._network.satellite(spec.origin).plmm
        if (
            yield from plmm.reserve(self._env, raw, spec.raw_size_gb, self._tolerance_s)
        ):
            self._ledger.mark_complete(raw)
        else:
            self._lost_raw.append(spec.id)

    def _plan(self, epochs: tuple[Epoch, ...]) -> Generator[simpy.Event, object]:
        for epoch in epochs:
            yield self._env.timeout(max(0.0, epoch.start_s - self._env.now))
            yield self._env.timeout(
                0
            )  # the arrivals of this instant enter the snapshot
            arrived, self._arrived = self._arrived, []
            decision = self._rolling.plan_epoch(epoch, arrived)
            if decision is not None:
                self._apply(decision, epoch)

    def _apply(self, decision: PlanningDecision, epoch: Epoch) -> None:
        """Record the decision of ``epoch`` and install its plan."""
        now = self._env.now
        for request_id in decision.rejected:
            self._records[request_id].move(RequestStatus.REJECTED, now)
            spec = self._specs[request_id]
            self._network.satellite(spec.origin).plmm.release(
                DataKey(spec.id, 0, spec.origin)
            )
        accepted: dict[str, RequestRuntime] = {}
        for request_id in _accepted_ids(decision.plan):
            record = self._records[request_id]
            record.move(RequestStatus.ACCEPTED, now)
            accepted[request_id] = RequestRuntime(
                self._env,
                self._specs[request_id],
                record,
                self._ledger,
                self._network.satellites,
                self._network.constellation.ground_station.id,
                self._rolling,
            )
        self._runtimes.update(accepted)
        arrival_s = plan_arrival_times(self._network.constellation, epoch.ready_s)
        self._installer.install(decision.plan, arrival_s, accepted)


def _accepted_ids(plan: EpochPlan) -> list[str]:
    """The requests with an action in ``plan``, in the order of their first action."""
    ids = [t.request_id for t in plan.tasks] + [t.request_id for t in plan.transfers]
    return list(dict.fromkeys(ids))
