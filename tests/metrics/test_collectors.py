"""Tests of the collectors of the bus, fed with hand-made notifications.

Satellite A computes in [0, 100]; the link A-B is always available, the link A-GS is visible in
[10, 30]. The simulation ends at 200 s.
"""

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.plan import EpochPlan, PlannedTask, PlannedTransfer
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.metrics.as_run import AsRunCollector
from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.metrics.epochs import EpochCollector
from satedge_simulator.metrics.plmm import PlmmCollector
from satedge_simulator.metrics.resources import ResourceCollector, ResourceUsage
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import (
    EpochPlanned,
    PlmmChanged,
    TaskEnded,
    TaskStarted,
    TransferEnded,
    TransferStarted,
)

END = 200.0


def constellation() -> Constellation:
    a = Satellite("A", 10.0, 1.0, WindowSet([Window(0.0, 100.0)]))
    b = Satellite("B", 10.0, 1.0, WindowSet([Window(0.0, 100.0)]))
    return Constellation(
        [Plane(1, (a, b), com="A")],
        GroundStation("GS"),
        [
            Link("A", "B", 1.0, 0.01, AlwaysAvailable()),
            Link(
                "A",
                "GS",
                1.0,
                0.01,
                WindowedAvailability(WindowSet([Window(10.0, 30.0)])),
            ),
        ],
    )


def test_resources_count_the_time_held_over_the_time_available() -> None:
    bus = EventBus()
    collector = ResourceCollector(constellation())
    collector.attach(bus)
    bus.publish(TaskStarted(10.0, "R1", 0, "A"))
    bus.publish(TaskEnded(30.0, "R1", 0, "A", completed=True))
    bus.publish(TaskStarted(40.0, "R2", 0, "A"))
    bus.publish(TaskEnded(45.0, "R2", 0, "A", completed=False))  # stopped: still held
    bus.publish(TaskStarted(190.0, "R3", 0, "B"))  # still running at the end
    bus.publish(TransferStarted(12.0, "R1", 1, "A", "GS"))
    bus.publish(TransferEnded(17.0, "R1", 1, "A", "GS", completed=True))
    hpcs = collector.hpcs(END)
    assert hpcs["A"] == ResourceUsage(25.0, 100.0)
    assert hpcs["A"].utilization == 0.25
    assert hpcs["B"] == ResourceUsage(10.0, 100.0)
    arcs = collector.arcs(END)
    assert arcs[("A", "GS")] == ResourceUsage(5.0, 20.0)
    assert arcs[("GS", "A")] == ResourceUsage(0.0, 20.0)
    assert arcs[("A", "B")] == ResourceUsage(0.0, END)


def test_a_resource_never_available_has_no_utilization() -> None:
    assert ResourceUsage(0.0, 0.0).utilization is None


def test_the_plmm_mean_is_weighted_by_time() -> None:
    bus = EventBus()
    collector = PlmmCollector(constellation())
    collector.attach(bus)
    bus.publish(PlmmChanged(20.0, "A", 4.0))
    bus.publish(PlmmChanged(70.0, "A", 6.0))
    bus.publish(PlmmChanged(120.0, "A", 2.0))
    usage = collector.usage(END)
    # 4 Gb for 50 s, 6 Gb for 50 s, 2 Gb for 80 s: 660 Gb·s over 200 s
    assert usage["A"].mean_gb == pytest.approx(3.3)
    assert usage["A"].peak_gb == 6.0
    assert usage["A"].peak_ratio == pytest.approx(0.6)
    assert usage["B"].mean_gb == 0.0


def test_epochs_sum_the_decisions_and_count_the_overruns() -> None:
    bus = EventBus()
    collector = EpochCollector()
    collector.attach(bus)
    bus.publish(EpochPlanned(50.0, 0, 100.0, 3, 2, 1, 40.0, 0))
    bus.publish(EpochPlanned(950.0, 1, 1000.0, 2, 1, 1, 60.0, 2))  # 60 s > 50 s of lead
    metrics = collector.metrics()
    assert (metrics.epochs, metrics.new, metrics.accepted, metrics.rejected) == (
        2,
        5,
        3,
        2,
    )
    assert metrics.solver_time == Distribution.of([40.0, 60.0])
    assert (metrics.overruns, metrics.max_unreachable) == (1, 2)


def test_the_as_run_keeps_the_completed_executions_with_their_actual_instants() -> None:
    bus = EventBus()
    collector = AsRunCollector()
    collector.attach(bus)
    bus.publish(TaskStarted(10.5, "R1", 0, "A"))
    bus.publish(TaskEnded(30.5, "R1", 0, "A", completed=True))
    bus.publish(TaskStarted(40.0, "R2", 0, "A"))
    bus.publish(TaskEnded(45.0, "R2", 0, "A", completed=False))
    bus.publish(TransferStarted(32.0, "R1", 1, "A", "GS"))
    bus.publish(TransferEnded(37.0, "R1", 1, "A", "GS", completed=True))
    as_run = collector.as_run()
    assert as_run.tasks == (PlannedTask("R1", 0, "A", 10.5, 30.5),)
    assert as_run.transfers == (PlannedTransfer("R1", 1, "A", "GS", 32.0, 37.0),)
    assert as_run.of_requests({"R2"}).tasks == ()
    plan = EpochPlan(
        tasks=(PlannedTask("R1", 0, "A", 10.0, 30.0),),
        transfers=(PlannedTransfer("R1", 1, "A", "GS", 32.0, 37.0),),
    )
    assert as_run.deviation([plan]) == Distribution.of([0.5, 0.0])
