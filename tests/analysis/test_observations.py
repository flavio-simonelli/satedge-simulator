"""Tests of the observations of a run and of their means over an interval."""

import pytest

from satedge_simulator.analysis.observations import (
    Observation,
    RunObservations,
    Statistic,
    TimeSeriesCollector,
    _per_request,
)
from satedge_simulator.domain.intervals import Window
from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.workload import Priority, RequestSpec, TaskSpec
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import PlmmChanged, TaskEnded, TaskStarted


def test_per_request_means_take_the_observations_of_the_interval() -> None:
    run = RunObservations(
        {Statistic.RESPONSE: (Observation(10.0, 100.0), Observation(30.0, 300.0))},
        (),
        (),
        (),
        50.0,
    )
    assert run.mean(Statistic.RESPONSE, 0.0, 50.0) == 200.0
    assert run.mean(Statistic.RESPONSE, 0.0, 30.0) == 100.0  # the interval is half open
    assert run.mean(Statistic.RESPONSE, 40.0, 50.0) is None


def test_the_hpc_utilization_is_the_time_held_over_the_time_open() -> None:
    windows = (Window(0.0, 100.0), Window(0.0, 100.0))  # two satellites
    run = RunObservations({}, ((10.0, 60.0),), windows, (), 100.0)
    assert run.mean(Statistic.HPC_UTILIZATION, 0.0, 100.0) == pytest.approx(50 / 200)
    assert run.mean(Statistic.HPC_UTILIZATION, 50.0, 100.0) == pytest.approx(10 / 100)
    assert (
        RunObservations({}, (), (), (), 1.0).mean(Statistic.HPC_UTILIZATION, 0.0, 1.0)
        is None
    )


def test_the_plmm_occupancy_is_a_time_average_of_its_steps() -> None:
    run = RunObservations({}, (), (), ((10.0, 4.0), (30.0, 6.0)), 50.0)
    # 0 Gb on [0, 10), 4 Gb on [10, 30), 6 Gb on [30, 50)
    assert run.mean(Statistic.PLMM_OCCUPANCY, 0.0, 50.0) == pytest.approx(
        (4 * 20 + 6 * 20) / 50
    )
    assert run.mean(Statistic.PLMM_OCCUPANCY, 20.0, 40.0) == pytest.approx(
        (4 * 10 + 6 * 10) / 20
    )


def test_the_collector_records_holds_and_the_total_memory() -> None:
    bus = EventBus()
    collector = TimeSeriesCollector()
    collector.attach(bus)
    bus.publish(TaskStarted(5.0, "R1", 0, "A"))
    bus.publish(TaskEnded(15.0, "R1", 0, "A", completed=True))
    bus.publish(TaskStarted(40.0, "R2", 0, "B"))  # still held at the end
    bus.publish(PlmmChanged(1.0, "A", 2.0))
    bus.publish(PlmmChanged(2.0, "B", 3.0))
    bus.publish(PlmmChanged(2.0, "A", 0.0))  # same instant: the last total wins
    assert collector.busy(end_s=50.0) == ((5.0, 15.0), (40.0, 50.0))
    assert collector.plmm_steps == ((1.0, 2.0), (2.0, 3.0))


def record(*moves: tuple[float, RequestStatus]) -> RequestRecord:
    r = RequestRecord("R1", history=[(10.0, RequestStatus.ARRIVED)])
    r.move(RequestStatus.QUEUED, 10.0)
    for at, status in moves:
        r.move(status, at)
    return r


def test_the_records_give_the_per_request_observations() -> None:
    spec = RequestSpec(
        "R1", Priority.URGENT, "A", 10.0, 20.0, 1000.0, 1.0, (TaskSpec(1.0, 1.0),)
    )
    delivered = _per_request(
        {
            "R1": record(
                (50.0, RequestStatus.ACCEPTED), (500.0, RequestStatus.DELIVERED_ON_TIME)
            )
        },
        [spec],
    )
    assert delivered[Statistic.ACCEPTANCE] == (Observation(50.0, 1.0),)
    assert delivered[Statistic.RESPONSE] == (Observation(500.0, 480.0),)
    assert delivered[Statistic.ON_TIME] == (Observation(500.0, 1.0),)
    failed = _per_request(
        {"R1": record((50.0, RequestStatus.ACCEPTED), (90.0, RequestStatus.FAILED))},
        [spec],
    )
    assert failed[Statistic.RESPONSE] == ()
    assert failed[Statistic.ON_TIME] == (Observation(90.0, 0.0),)
    open_ = _per_request({"R1": record((50.0, RequestStatus.REJECTED))}, [spec])
    assert open_[Statistic.ACCEPTANCE] == (Observation(50.0, 0.0),)
    assert open_[Statistic.ON_TIME] == ()
