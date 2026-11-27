"""Tests of the runtime of an accepted request: delivery, failure, and cleanup after a failure.

The request R1 has its raw data (4 Gb) on A and one task (8 s, 1 Gb of output). On an HPC at
1 Gbps the task lasts 4 + 8 + 1 = 13 s: planned at 10 s, it ends at 23 s and writes its output
from 22 s. The output goes from A to the ground station at 30 s on a link at 1 Gbps with 0.5 s
of latency, so it is delivered at 31.5 s.
"""

from collections.abc import Generator
from dataclasses import dataclass, field

import pytest
import simpy

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.plan import PlannedTask, PlannedTransfer
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Availability,
    Link,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.domain.violations import ViolationKind
from satedge_simulator.errors import StateError
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.links import LinkRuntime
from satedge_simulator.runtime.requests import RequestRuntime
from satedge_simulator.runtime.satellite import SatelliteRuntime
from satedge_simulator.runtime.tasks import run_task
from satedge_simulator.runtime.transfers import run_transfer

EPS = 1e-4
TASK_SPEC = TaskSpec(execution_s=8.0, output_size_gb=1.0)
TASK = PlannedTask("R1", 0, "A", start_s=10.0, end_s=23.0)
DOWNLINK = PlannedTransfer("R1", 1, "A", "GS", start_s=30.0, end_s=31.0)
RAW = DataKey("R1", 0, "A")
OUTPUT = DataKey("R1", 1, "A")

SAT_A = Satellite("A", 100.0, 1.0, WindowSet())


def request(deadline_s: float = 100.0) -> RequestSpec:
    return RequestSpec(
        id="R1",
        priority=Priority.URGENT,
        origin=SAT_A,
        arrival_s=0.0,
        release_s=0.0,
        deadline_s=deadline_s,
        raw_size_gb=4.0,
        tasks=(TASK_SPEC,),
    )


def accepted() -> RequestRecord:
    record = RequestRecord("R1")
    record.move(RequestStatus.QUEUED, 0.0)
    record.move(RequestStatus.ACCEPTED, 0.0)
    return record


@dataclass
class Listener:
    delivered: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def on_delivered(self, request_id: str) -> None:
        self.delivered.append(request_id)

    def on_failed(self, request_id: str) -> None:
        self.failed.append(request_id)


@dataclass
class Harness:
    env: simpy.Environment
    ledger: DataLedger
    a: SatelliteRuntime
    b: SatelliteRuntime
    downlink: LinkRuntime
    record: RequestRecord
    listener: Listener
    runtime: RequestRuntime

    def raw_on_a(self) -> None:
        def process() -> Generator[simpy.Event, object]:
            yield from self.a.plmm.reserve(self.env, RAW, 4.0, EPS)
            self.ledger.mark_complete(RAW)

        self.env.process(process())

    def task(self, tolerance_s: float = EPS) -> bool:
        return self.runtime.run(
            run_task(
                self.env,
                TASK,
                self.a,
                self.ledger,
                self.runtime.report,
                tolerance_s,
                TASK_SPEC,
                4.0,
            )
        )

    def send(
        self,
        transfer: PlannedTransfer,
        link: LinkRuntime,
        receiver: SatelliteRuntime | None,
    ) -> bool:
        return self.runtime.run(
            run_transfer(
                self.env,
                transfer,
                link,
                self.a,
                receiver,
                self.ledger,
                self.runtime.report,
                EPS,
                1.0,
            )
        )

    def fail_at(self, instant: float) -> None:
        def process() -> Generator[simpy.Event, object]:
            yield self.env.timeout(instant)
            self.runtime.fail()

        self.env.process(process())


def satellite(node: str, env: simpy.Environment) -> SatelliteRuntime:
    return SatelliteRuntime(
        env, Satellite(node, 10.0, 1.0, WindowSet([Window(0.0, 1000.0)])), EPS
    )


def harness(deadline_s: float = 100.0, downlink: Availability | None = None) -> Harness:
    env = simpy.Environment()
    ledger = DataLedger(env)
    a, b = satellite("A", env), satellite("B", env)
    link = Link("A", "GS", 1.0, 0.5, downlink or AlwaysAvailable())
    record, listener = accepted(), Listener()
    runtime = RequestRuntime(
        env, request(deadline_s), record, ledger, (a, b), "GS", listener
    )
    return Harness(
        env,
        ledger,
        a,
        b,
        LinkRuntime(env, link, "A", "GS", EPS),
        record,
        listener,
        runtime,
    )


def test_the_request_is_delivered_when_its_output_is_complete_on_the_ground() -> None:
    h = harness()
    h.raw_on_a()
    h.task()
    h.send(DOWNLINK, h.downlink, None)
    h.env.run()
    assert h.record.status is RequestStatus.DELIVERED_ON_TIME
    assert h.record.history[-1] == (31.5, RequestStatus.DELIVERED_ON_TIME)
    assert h.listener.delivered == ["R1"]
    assert h.runtime.violations == ()
    assert h.a.plmm.level_gb == 0.0


def test_a_delivery_after_the_deadline_is_late() -> None:
    h = harness(deadline_s=31.0)
    h.raw_on_a()
    h.task()
    h.send(DOWNLINK, h.downlink, None)
    h.env.run()
    assert h.record.status is RequestStatus.DELIVERED_LATE
    assert h.listener.delivered == ["R1"]


def test_the_first_violation_fails_the_request_and_stops_its_other_actions() -> None:
    h = harness()  # no raw data: the task cannot start
    h.task()
    h.send(DOWNLINK, h.downlink, None)
    h.env.run()
    assert h.record.status is RequestStatus.FAILED
    instant, status = h.record.history[-1]
    assert instant == pytest.approx(10.0 + EPS)
    assert status is RequestStatus.FAILED
    assert [v.kind for v in h.runtime.violations] == [ViolationKind.DATA_NOT_READY]
    assert h.listener.failed == ["R1"]
    assert h.listener.delivered == []


def test_a_failure_frees_the_data_of_the_request_from_every_plmm() -> None:
    # The task runs, then the downlink is not visible at 30 s: the output resting on A must go,
    # while the item of another request stays.
    h = harness(downlink=WindowedAvailability(WindowSet([Window(100.0, 200.0)])))
    other = DataKey("X", 0, "A")

    def other_request() -> Generator[simpy.Event, object]:
        yield from h.a.plmm.reserve(h.env, other, 2.0, EPS)

    h.env.process(other_request())
    h.raw_on_a()
    h.task()
    h.send(DOWNLINK, h.downlink, None)
    h.env.run()
    assert [v.kind for v in h.runtime.violations] == [ViolationKind.LINK_WINDOW]
    assert h.a.plmm.occupied_gb(OUTPUT) == 0.0
    assert h.a.plmm.level_gb == 2.0


def test_a_failure_during_a_task_frees_the_hpc_and_the_output_being_written() -> None:
    h = harness()
    h.raw_on_a()
    h.task()
    h.fail_at(22.5)  # the output is being written since 22 s
    h.env.run()
    assert h.record.status is RequestStatus.FAILED
    assert h.runtime.violations == ()
    assert h.a.hpc.count == 0
    assert h.a.plmm.level_gb == 0.0
    assert not h.ledger.is_complete(OUTPUT)


def test_a_failure_while_waiting_for_the_hpc_withdraws_the_request_for_it() -> None:
    h = harness()
    h.raw_on_a()

    def occupier() -> Generator[simpy.Event, object]:
        request = h.a.hpc.request()
        yield request
        yield h.env.timeout(20.0)
        h.a.hpc.release(request)

    h.env.process(occupier())
    h.task(tolerance_s=5.0)  # waits for the HPC from 10 s
    h.fail_at(12.0)
    h.env.run()
    assert h.a.hpc.count == 0
    assert len(h.a.hpc.queue) == 0


def test_a_failure_during_a_transfer_frees_the_channel_and_the_reception() -> None:
    h = harness()
    h.raw_on_a()
    crosslink = LinkRuntime(
        h.env, Link("A", "B", 1.0, 0.2, AlwaysAvailable()), "A", "B", EPS
    )
    h.task()
    h.send(PlannedTransfer("R1", 1, "A", "B", start_s=30.0, end_s=31.0), crosslink, h.b)
    h.fail_at(30.5)  # B holds the item since 30.2 s
    h.env.run()
    assert crosslink.channel.count == 0
    assert h.b.plmm.level_gb == 0.0
    assert h.a.plmm.level_gb == 0.0
    assert not h.ledger.is_complete(DataKey("R1", 1, "B"))


def test_an_action_of_a_failed_request_does_not_start() -> None:
    h = harness()
    h.runtime.fail()
    assert not h.task()
    h.env.run()
    assert h.a.hpc.count == 0
    assert h.listener.failed == ["R1"]


def test_a_failure_after_the_delivery_changes_nothing() -> None:
    h = harness()
    h.raw_on_a()
    h.task()
    h.send(DOWNLINK, h.downlink, None)
    h.fail_at(50.0)
    h.env.run()
    assert h.record.status is RequestStatus.DELIVERED_ON_TIME
    assert h.listener.failed == []


def test_the_runtime_needs_an_accepted_request() -> None:
    env = simpy.Environment()
    spec = request()
    record = RequestRecord("R1")
    ledger = DataLedger(env)
    listener = Listener()
    with pytest.raises(StateError, match="accettata"):
        RequestRuntime(env, spec, record, ledger, (), "GS", listener)
