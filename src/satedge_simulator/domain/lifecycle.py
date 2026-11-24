"""Lifecycle of a request: its states, and the transitions the simulation may make between them."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from satedge_simulator.errors import StateError


class RequestStatus(StrEnum):
    """State of a request during the simulation."""

    ARRIVED = "arrived"
    QUEUED = "queued"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DELIVERED_ON_TIME = "delivered_on_time"
    DELIVERED_LATE = "delivered_late"
    FAILED = "failed"
    UNFINISHED = "unfinished"


_TRANSITIONS: Mapping[RequestStatus, frozenset[RequestStatus]] = MappingProxyType(
    {
        RequestStatus.ARRIVED: frozenset(
            {RequestStatus.QUEUED, RequestStatus.UNFINISHED}
        ),
        RequestStatus.QUEUED: frozenset(
            {RequestStatus.ACCEPTED, RequestStatus.REJECTED, RequestStatus.UNFINISHED}
        ),
        RequestStatus.ACCEPTED: frozenset(
            {
                RequestStatus.DELIVERED_ON_TIME,
                RequestStatus.DELIVERED_LATE,
                RequestStatus.FAILED,
                RequestStatus.UNFINISHED,
            }
        ),
    }
)


@dataclass(slots=True)
class RequestRecord:
    """The state of one request, with the history of its transitions.

    A record is created in ``ARRIVED`` and moves only along the transitions the table allows.
    Each move is kept with its instant, so the history can be reported in full.

    Attributes:
        request_id: Identifier of the request.
        status: Current state.
        history: Pairs ``(instant_s, status)``, from the arrival on.
    """

    request_id: str
    status: RequestStatus = RequestStatus.ARRIVED
    history: list[tuple[float, RequestStatus]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.history:
            self.history.append((0.0, self.status))

    @property
    def is_final(self) -> bool:
        """Whether the request can no longer change state."""
        return self.status not in _TRANSITIONS

    def move(self, target: RequestStatus, at_s: float) -> None:
        """Move the request to ``target`` at ``at_s``.

        Raises:
            StateError: If the transition is not allowed from the current state. This is a
                defect of the simulator, not a violation of the plan.
        """
        if target not in _TRANSITIONS.get(self.status, frozenset()):
            raise StateError(
                f"request {self.request_id}: cannot go from {self.status} to {target}"
            )
        self.status = target
        self.history.append((at_s, target))
