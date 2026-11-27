"""Tests of the indicators of the requests, from hand-made records."""

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.topology import Satellite
from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.metrics.requests import request_metrics

SAT_A = Satellite("A", 100.0, 1.0, WindowSet())


def spec(request_id: str, priority: Priority = Priority.URGENT) -> RequestSpec:
    return RequestSpec(
        id=request_id,
        priority=priority,
        origin=SAT_A,
        arrival_s=10.0,
        release_s=20.0,
        deadline_s=100.0,
        raw_size_gb=1.0,
        tasks=(TaskSpec(1.0, 1.0),),
    )


def record(request_id: str, *moves: tuple[float, RequestStatus]) -> RequestRecord:
    r = RequestRecord(request_id, history=[(10.0, RequestStatus.ARRIVED)])
    r.move(RequestStatus.QUEUED, 10.0)
    for at, status in moves:
        r.move(status, at)
    return r


def test_counts_and_times_of_one_class() -> None:
    accepted = (50.0, RequestStatus.ACCEPTED)
    records = {
        "on_time": record("on_time", accepted, (80.0, RequestStatus.DELIVERED_ON_TIME)),
        "late": record("late", accepted, (130.0, RequestStatus.DELIVERED_LATE)),
        "failed": record("failed", accepted, (60.0, RequestStatus.FAILED)),
        "rejected": record("rejected", (50.0, RequestStatus.REJECTED)),
        "open": record("open", (200.0, RequestStatus.UNFINISHED)),
    }
    urgent, non_urgent = request_metrics(
        records, [spec(i) for i in records] + [spec("never_arrived")]
    )
    assert urgent.priority is Priority.URGENT
    assert (urgent.arrived, urgent.accepted, urgent.rejected) == (5, 3, 1)
    assert (urgent.delivered_on_time, urgent.delivered_late) == (1, 1)
    assert (urgent.failed, urgent.unfinished) == (1, 1)
    assert urgent.response_from_release == Distribution.of([60.0, 110.0])
    assert urgent.response_from_arrival == Distribution.of([70.0, 120.0])
    assert urgent.tardiness == Distribution.of([0.0, 30.0])
    assert non_urgent.arrived == 0
    assert non_urgent.response_from_release == Distribution(count=0)


def test_the_classes_are_kept_apart() -> None:
    records = {"U": record("U"), "N": record("N")}
    urgent, non_urgent = request_metrics(
        records, [spec("U"), spec("N", Priority.NON_URGENT)]
    )
    assert (urgent.arrived, non_urgent.arrived) == (1, 1)
