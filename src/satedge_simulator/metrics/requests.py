"""Indicators of the requests, per priority class, from their final records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.requests import Priority, RequestSpec
from satedge_simulator.metrics.distribution import Distribution

_DELIVERED = frozenset({RequestStatus.DELIVERED_ON_TIME, RequestStatus.DELIVERED_LATE})


@dataclass(frozen=True, slots=True)
class ClassMetrics:
    """The requests of one priority class.

    Attributes:
        priority: The class.
        arrived: Requests that reached the ground segment before the end.
        accepted: Requests the planner accepted, whatever happened to them afterwards.
        rejected: Requests the planner rejected.
        delivered_on_time: Requests delivered by their deadline.
        delivered_late: Requests delivered after their deadline.
        failed: Accepted requests whose execution failed.
        unfinished: Requests still open at the end.
        response_from_release: Delivery minus the release of the raw data, as in the objective
            of the MILP model.
        response_from_arrival: Delivery minus the arrival at the ground segment, as the user
            sees it: it includes the wait for the epoch.
        tardiness: Delivery minus the deadline, zero when on time.
    """

    priority: Priority
    arrived: int
    accepted: int
    rejected: int
    delivered_on_time: int
    delivered_late: int
    failed: int
    unfinished: int
    response_from_release: Distribution
    response_from_arrival: Distribution
    tardiness: Distribution


def request_metrics(
    records: Mapping[str, RequestRecord], requests: Iterable[RequestSpec]
) -> tuple[ClassMetrics, ...]:
    """The indicators of each priority class, urgent first.

    Only the requests with a record count: a request that arrives after the end has none.
    """
    by_class: dict[Priority, list[tuple[RequestSpec, RequestRecord]]] = {
        p: [] for p in Priority
    }
    for spec in requests:
        if spec.id in records:
            by_class[spec.priority].append((spec, records[spec.id]))
    return tuple(_class_metrics(p, pairs) for p, pairs in by_class.items())


def _class_metrics(
    priority: Priority, pairs: list[tuple[RequestSpec, RequestRecord]]
) -> ClassMetrics:
    def count(status: RequestStatus) -> int:
        return sum(1 for _, record in pairs if record.status is status)

    delivered = [
        (spec, record.history[-1][0])
        for spec, record in pairs
        if record.status in _DELIVERED
    ]
    return ClassMetrics(
        priority=priority,
        arrived=len(pairs),
        accepted=sum(1 for _, r in pairs if _was(r, RequestStatus.ACCEPTED)),
        rejected=count(RequestStatus.REJECTED),
        delivered_on_time=count(RequestStatus.DELIVERED_ON_TIME),
        delivered_late=count(RequestStatus.DELIVERED_LATE),
        failed=count(RequestStatus.FAILED),
        unfinished=count(RequestStatus.UNFINISHED),
        response_from_release=Distribution.of(at - s.release_s for s, at in delivered),
        response_from_arrival=Distribution.of(at - s.arrival_s for s, at in delivered),
        tardiness=Distribution.of(max(0.0, at - s.deadline_s) for s, at in delivered),
    )


def _was(record: RequestRecord, status: RequestStatus) -> bool:
    return any(s is status for _, s in record.history)
