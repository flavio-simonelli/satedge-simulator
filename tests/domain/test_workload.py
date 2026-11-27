"""Tests of the requests and of the HPC occupancy of their tasks."""

import pytest

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.topology import Satellite
from satedge_simulator.errors import DomainError

SAT = Satellite("P1-S3", 100.0, 1.0, WindowSet())


def request(
    *,
    request_id: str = "R1",
    release_s: float = 0.0,
    deadline_s: float = 7200.0,
    tasks: tuple[TaskSpec, ...] = (TaskSpec(120.0, 0.5), TaskSpec(90.0, 0.001)),
) -> RequestSpec:
    return RequestSpec(
        id=request_id,
        priority=Priority.URGENT,
        origin=SAT,
        arrival_s=0.0,
        release_s=release_s,
        deadline_s=deadline_s,
        raw_size_gb=8.0,
        tasks=tasks,
    )


def test_data_sizes_are_raw_then_each_output() -> None:
    assert request().data_sizes_gb() == (8.0, 0.5, 0.001)
    assert request().output_size_gb == 0.001


def test_hpc_occupancy_adds_read_execution_and_write() -> None:
    r = request()
    # task 0: read 8 Gb, execute 120 s, write 0.5 Gb, at 1 Gbps
    assert r.hpc_occupancy_s(0, hpc_rate_gbps=1.0) == pytest.approx(8.0 + 120.0 + 0.5)
    # task 1: read 0.5 Gb, execute 90 s, write 0.001 Gb
    assert r.hpc_occupancy_s(1, hpc_rate_gbps=1.0) == pytest.approx(0.5 + 90.0 + 0.001)


def test_faster_hpc_link_shortens_only_the_io() -> None:
    assert request().hpc_occupancy_s(0, hpc_rate_gbps=2.0) == pytest.approx(
        4.0 + 120.0 + 0.25
    )


def test_pipeline_must_have_a_task() -> None:
    with pytest.raises(DomainError):
        request(tasks=())


def test_deadline_cannot_precede_the_release() -> None:
    with pytest.raises(DomainError):
        request(release_s=100.0, deadline_s=50.0)


def test_task_values_must_be_positive() -> None:
    with pytest.raises(DomainError):
        TaskSpec(0.0, 1.0)
    with pytest.raises(DomainError):
        TaskSpec(10.0, -1.0)


def test_request_id_must_not_be_empty() -> None:
    with pytest.raises(DomainError):
        request(request_id="")


def test_arrival_cannot_follow_the_release() -> None:
    with pytest.raises(DomainError):
        RequestSpec(
            id="R1",
            priority=Priority.URGENT,
            origin=SAT,
            arrival_s=200.0,
            release_s=100.0,
            deadline_s=7200.0,
            raw_size_gb=8.0,
            tasks=(TaskSpec(120.0, 0.5),),
        )


def test_requests_with_the_same_id_are_distinct() -> None:
    first, second = request(), request()
    assert first.id == second.id
    assert first != second
    assert len({first, second}) == 2
