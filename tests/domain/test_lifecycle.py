"""Tests of the lifecycle of a request."""

import pytest

from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.errors import StateError


def test_a_request_is_accepted_then_delivered() -> None:
    record = RequestRecord("R1")
    record.move(RequestStatus.QUEUED, 10.0)
    record.move(RequestStatus.ACCEPTED, 10.0)
    record.move(RequestStatus.DELIVERED_ON_TIME, 500.0)
    assert record.status is RequestStatus.DELIVERED_ON_TIME
    assert record.is_final
    assert record.history[-1] == (500.0, RequestStatus.DELIVERED_ON_TIME)


def test_history_starts_at_the_arrival() -> None:
    assert RequestRecord("R1").history == [(0.0, RequestStatus.ARRIVED)]


def test_a_rejected_request_cannot_be_accepted_later() -> None:
    record = RequestRecord("R1")
    record.move(RequestStatus.QUEUED, 1.0)
    record.move(RequestStatus.REJECTED, 2.0)
    with pytest.raises(StateError, match="non può passare da rejected a accepted"):
        record.move(RequestStatus.ACCEPTED, 3.0)


def test_a_request_cannot_skip_the_queue() -> None:
    with pytest.raises(StateError):
        RequestRecord("R1").move(RequestStatus.ACCEPTED, 1.0)


def test_a_failed_request_is_final() -> None:
    record = RequestRecord("R1")
    record.move(RequestStatus.QUEUED, 1.0)
    record.move(RequestStatus.ACCEPTED, 1.0)
    record.move(RequestStatus.FAILED, 2.0)
    assert record.is_final
    with pytest.raises(StateError):
        record.move(RequestStatus.DELIVERED_LATE, 3.0)


def test_an_arrival_can_end_unfinished_at_the_horizon() -> None:
    record = RequestRecord("R1")
    record.move(RequestStatus.UNFINISHED, 100.0)
    assert record.is_final
