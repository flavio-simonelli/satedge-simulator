"""The notifications of the runtime: what happened, and when.

Each notification is an immutable record with the instant it happened at, ``time``, in
seconds. The runtime publishes them on the bus and does not know who listens: the metrics and
the event log are subscribers.
"""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.domain.violations import ViolationKind


@dataclass(frozen=True, slots=True)
class Notification:
    """Base of every notification.

    Attributes:
        time: Instant the notification refers to, in seconds.
    """

    time: float


@dataclass(frozen=True, slots=True)
class RequestArrived(Notification):
    """A request reached the ground segment and waits in the queue."""

    request_id: str


@dataclass(frozen=True, slots=True)
class RequestAccepted(Notification):
    """The planner accepted a request in an epoch."""

    request_id: str
    epoch: int


@dataclass(frozen=True, slots=True)
class RequestRejected(Notification):
    """The planner rejected a request in an epoch: the rejection is final."""

    request_id: str
    epoch: int
    reason: str


@dataclass(frozen=True, slots=True)
class RequestDelivered(Notification):
    """The final output of a request is complete on the ground station."""

    request_id: str
    on_time: bool


@dataclass(frozen=True, slots=True)
class RequestFailed(Notification):
    """A request failed: its actions stopped and its data left the PLMMs."""

    request_id: str


@dataclass(frozen=True, slots=True)
class ViolationRaised(Notification):
    """An action of the plan could not be carried out as planned."""

    request_id: str
    kind: ViolationKind
    node: NodeId


@dataclass(frozen=True, slots=True)
class EpochPlanned(Notification):
    """The ground segment decided an epoch.

    Attributes:
        epoch: Index of the epoch.
        ready_s: Instant the plan is ready, at the opening of the contact.
        new: Requests the planner was asked to decide.
        accepted: Requests it accepted.
        rejected: Requests it rejected.
        solver_time_s: Seconds the planner spent.
        unreachable: Satellites the plan cannot reach.
    """

    epoch: int
    ready_s: float
    new: int
    accepted: int
    rejected: int
    solver_time_s: float
    unreachable: int


@dataclass(frozen=True, slots=True)
class PlanInstalled(Notification):
    """The plan of an epoch reached a satellite that has actions in it."""

    epoch: int
    satellite: NodeId


@dataclass(frozen=True, slots=True)
class TaskStarted(Notification):
    """A task took the HPC of its satellite."""

    request_id: str
    task_index: int
    satellite: NodeId


@dataclass(frozen=True, slots=True)
class TaskEnded(Notification):
    """A task released the HPC: at its end if ``completed``, earlier if it was stopped."""

    request_id: str
    task_index: int
    satellite: NodeId
    completed: bool


@dataclass(frozen=True, slots=True)
class TransferStarted(Notification):
    """A transmission took one direction of a link."""

    request_id: str
    data_index: int
    source: NodeId
    target: NodeId


@dataclass(frozen=True, slots=True)
class TransferEnded(Notification):
    """A transmission released its channel: at its end if ``completed``, earlier if stopped."""

    request_id: str
    data_index: int
    source: NodeId
    target: NodeId
    completed: bool


@dataclass(frozen=True, slots=True)
class TransferReceived(Notification):
    """The last bits of a transmission reached its target: the item is complete there."""

    request_id: str
    data_index: int
    source: NodeId
    target: NodeId


@dataclass(frozen=True, slots=True)
class PlmmChanged(Notification):
    """The occupied memory of the PLMM of a satellite changed."""

    satellite: NodeId
    level_gb: float
