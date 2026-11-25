"""Rolling planner: the stateful part of the ground segment, which decides epoch after epoch.

It keeps two things between the epochs: the requests waiting for a decision, and the commitments,
which are the accepted requests not yet delivered, with their fixed actions. Everything else (the
epochs, the propagation of the plan, the planner itself) is computed from these, without state.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from satedge_simulator.domain.topology import Constellation
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.errors import PlannerError, StateError
from satedge_simulator.planning.epochs import Epoch
from satedge_simulator.planning.ports import (
    Commitment,
    Planner,
    PlanningDecision,
    PlanningSnapshot,
)
from satedge_simulator.planning.propagation import plan_arrival_times


class RollingPlanner:
    """Plans the epochs in order, and keeps the state the epochs share.

    Args:
        planner: The planner that decides each epoch, behind its port.
        constellation: The network the plans travel through.
    """

    def __init__(self, planner: Planner, constellation: Constellation) -> None:
        self._planner = planner
        self._constellation = constellation
        self._pending: list[RequestSpec] = []
        self._commitments: dict[str, Commitment] = {}

    @property
    def pending(self) -> tuple[RequestSpec, ...]:
        """Requests waiting for a decision, in arrival order."""
        return tuple(self._pending)

    @property
    def commitments(self) -> tuple[Commitment, ...]:
        """Accepted requests not yet delivered, in acceptance order."""
        return tuple(self._commitments.values())

    def plan_epoch(
        self, epoch: Epoch, arrived: Iterable[RequestSpec] = ()
    ) -> PlanningDecision | None:
        """Decide the epoch, and return the decision, or ``None`` if nothing was decided.

        ``None`` means that the planner was not called (no request is waiting) or that it failed:
        in both cases the pending requests stay pending for the next epoch. A rejection is final.
        """
        self._pending.extend(arrived)
        if not self._pending:
            return None
        new_requests = tuple(released_at(r, epoch.start_s) for r in self._pending)
        snapshot = PlanningSnapshot(
            epoch=epoch,
            constellation=self._constellation,
            new_requests=new_requests,
            commitments=self.commitments,
            plan_arrival_s=plan_arrival_times(self._constellation, epoch.ready_s),
        )
        try:
            decision = self._planner.plan(snapshot)
        except PlannerError:
            return None
        self._record(decision, new_requests)
        return decision

    def on_delivered(self, request_id: str) -> None:
        """The output of the request reached the ground station: it is no longer committed."""
        self._release_commitment(request_id)

    def on_failed(self, request_id: str) -> None:
        """The execution of the request failed: it is no longer committed."""
        self._release_commitment(request_id)

    def _record(
        self, decision: PlanningDecision, new_requests: tuple[RequestSpec, ...]
    ) -> None:
        by_id = {r.id: r for r in new_requests}
        accepted = {t.request_id for t in decision.plan.tasks} | {
            t.request_id for t in decision.plan.transfers
        }
        unknown = accepted - by_id.keys()
        if unknown:
            raise PlannerError(
                f"il planner ha accettato richieste che non gli erano state chieste: {sorted(unknown)}"
            )
        for request_id in accepted:
            self._commitments[request_id] = Commitment(
                request=by_id[request_id],
                tasks=tuple(
                    t for t in decision.plan.tasks if t.request_id == request_id
                ),
                transfers=tuple(
                    t for t in decision.plan.transfers if t.request_id == request_id
                ),
            )
        decided = accepted | set(decision.rejected)
        self._pending = [r for r in self._pending if r.id not in decided]

    def _release_commitment(self, request_id: str) -> None:
        if request_id not in self._commitments:
            raise StateError(f"la richiesta {request_id} non è impegnata")
        del self._commitments[request_id]


def released_at(request: RequestSpec, epoch_start_s: float) -> RequestSpec:
    """The request as an epoch sees it: none of its actions can start before the epoch."""
    return replace(request, release_s=max(request.release_s, epoch_start_s))
