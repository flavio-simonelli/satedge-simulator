"""Tests of the execution of a planned transfer on SimPy, with exact instants.

The link carries 2 Gbps with 0.5 s of latency, and the item is 4 Gb: the transmission lasts
2 s. Planned at 10 s, the receiver holds the item from 10.5 s, the sender frees it at 12 s and
the item is complete on the receiver at 12.5 s.
"""

from collections.abc import Generator
from dataclasses import dataclass, field

import pytest
import simpy

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.plan import PlannedTransfer
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Availability,
    Link,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.links import LinkRuntime
from satedge_simulator.runtime.satellite import SatelliteRuntime
from satedge_simulator.runtime.transfers import run_transfer

EPS = 1e-4
SIZE_GB = 4.0
TRANSFER = PlannedTransfer("R1", 0, "A", "B", start_s=10.0, end_s=12.0)
ON_SENDER = DataKey("R1", 0, "A")
ON_RECEIVER = DataKey("R1", 0, "B")


def satellite(node: str, env: simpy.Environment) -> SatelliteRuntime:
    return SatelliteRuntime(
        env, Satellite(node, 10.0, 1.0, WindowSet([Window(0.0, 1000.0)])), EPS
    )


@dataclass
class Harness:
    env: simpy.Environment
    ledger: DataLedger
    sender: SatelliteRuntime
    receiver: SatelliteRuntime | None
    link: LinkRuntime
    violations: list[Violation] = field(default_factory=list)
    results: list[bool] = field(default_factory=list)
    ended_at: list[float] = field(default_factory=list)

    def start(self, transfer: PlannedTransfer = TRANSFER) -> None:
        def process() -> Generator[simpy.Event, object]:
            outcome = yield from run_transfer(
                self.env,
                transfer,
                self.link,
                self.sender,
                self.receiver,
                self.ledger,
                self.violations.append,
                EPS,
                SIZE_GB,
            )
            self.results.append(outcome)
            self.ended_at.append(self.env.now)

        self.env.process(process())

    def data_on_sender_at(self, instant: float) -> None:
        def process() -> Generator[simpy.Event, object]:
            yield self.env.timeout(instant)
            yield from self.sender.plmm.reserve(self.env, ON_SENDER, SIZE_GB, EPS)
            self.ledger.mark_complete(ON_SENDER)

        self.env.process(process())

    def levels_at(self, *instants: float) -> dict[float, tuple[float, float]]:
        """PLMM levels of sender and receiver at each instant, filled while the run goes."""
        levels: dict[float, tuple[float, float]] = {}

        def probe(instant: float) -> Generator[simpy.Event, object]:
            yield self.env.timeout(instant)
            assert self.receiver is not None
            levels[instant] = (self.sender.plmm.level_gb, self.receiver.plmm.level_gb)

        for instant in instants:
            self.env.process(probe(instant))
        return levels


def harness(
    availability: Availability | None = None, latency_s: float = 0.5
) -> Harness:
    env = simpy.Environment()
    link = Link("A", "B", 2.0, latency_s, availability or AlwaysAvailable())
    return Harness(
        env,
        DataLedger(env),
        satellite("A", env),
        satellite("B", env),
        LinkRuntime(env, link, "A", "B", EPS),
    )


def visible(*windows: Window) -> WindowedAvailability:
    return WindowedAvailability(WindowSet(windows))


def test_the_item_is_complete_on_the_receiver_after_transmission_and_latency() -> None:
    h = harness()
    h.data_on_sender_at(0.0)
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.violations == []
    assert h.ended_at == [12.5]
    assert h.ledger.is_complete(ON_RECEIVER)


def test_the_receiver_holds_the_item_from_the_first_bits_the_sender_frees_it_at_the_last() -> (
    None
):
    h = harness()
    h.data_on_sender_at(0.0)
    levels = h.levels_at(10.25, 11.0, 12.25)
    h.start()
    h.env.run()
    assert levels == {
        10.25: (SIZE_GB, 0.0),
        11.0: (SIZE_GB, SIZE_GB),
        12.25: (0.0, SIZE_GB),
    }


def test_a_latency_longer_than_the_transmission_keeps_the_item_in_flight() -> None:
    h = harness(latency_s=3.0)
    h.data_on_sender_at(0.0)
    levels = h.levels_at(12.5, 13.5)
    h.start()
    h.env.run()
    assert levels == {12.5: (0.0, 0.0), 13.5: (0.0, SIZE_GB)}
    assert h.ended_at == [15.0]


def test_a_late_item_within_the_tolerance_shifts_the_whole_transfer() -> None:
    h = harness()
    h.data_on_sender_at(10.0 + EPS / 2)
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.ended_at == [pytest.approx(12.5 + EPS / 2)]


def test_an_item_too_late_on_the_sender_stops_the_transfer() -> None:
    h = harness()
    h.data_on_sender_at(10.0 + 2 * EPS)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [(v.kind, v.node) for v in h.violations] == [
        (ViolationKind.DATA_NOT_READY, "A")
    ]
    assert h.violations[0].at_s == pytest.approx(10.0 + EPS)


def test_a_busy_channel_is_a_violation() -> None:
    h = harness()
    h.data_on_sender_at(0.0)

    def occupier() -> Generator[simpy.Event, object]:
        request = h.link.channel.request()
        yield request
        yield h.env.timeout(20.0)
        h.link.channel.release(request)

    h.env.process(occupier())
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.LINK_BUSY]


def test_the_opposite_direction_does_not_occupy_the_channel() -> None:
    h = harness()
    h.data_on_sender_at(0.0)
    backwards = LinkRuntime(h.env, h.link.link, "B", "A", EPS)

    def occupier() -> Generator[simpy.Event, object]:
        request = backwards.channel.request()
        yield request
        yield h.env.timeout(20.0)
        backwards.channel.release(request)

    h.env.process(occupier())
    h.start()
    h.env.run()
    assert h.results == [True]


def test_a_window_closing_during_the_transmission_stops_it() -> None:
    h = harness(visible(Window(0.0, 11.0)))
    h.data_on_sender_at(0.0)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [(v.kind, v.node) for v in h.violations] == [
        (ViolationKind.LINK_WINDOW, "A")
    ]
    assert h.violations[0].at_s == pytest.approx(11.0 + EPS)
    assert h.receiver is not None
    assert h.receiver.plmm.level_gb == 0.0  # what the reception reserved is freed
    assert h.sender.plmm.occupied_gb(ON_SENDER) == SIZE_GB  # the sender keeps its copy
    assert h.link.channel.count == 0
    assert not h.ledger.is_complete(ON_RECEIVER)


def test_a_window_closing_before_the_last_bits_arrive_fails_the_transfer() -> None:
    # The transmission ends at 12 s, inside the window, but the last bits arrive at 12.5 s.
    h = harness(visible(Window(0.0, 12.0)))
    h.data_on_sender_at(0.0)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [(v.kind, v.node) for v in h.violations] == [
        (ViolationKind.LINK_WINDOW, "A")
    ]
    assert h.violations[0].at_s == pytest.approx(12.0 + EPS)
    assert h.receiver is not None
    assert h.receiver.plmm.level_gb == 0.0
    assert (
        h.sender.plmm.level_gb == 0.0
    )  # the sender freed its copy at the end of sending
    assert h.link.channel.count == 0
    assert not h.ledger.is_complete(ON_RECEIVER)


def test_the_channel_is_free_at_the_end_of_the_transmission() -> None:
    # With 3 s of latency the first item is in flight until 15 s, but the channel is free at
    # 12 s, so a second transfer planned at 12 s finds it free.
    h = harness(latency_s=3.0)
    h.data_on_sender_at(0.0)
    second = DataKey("R2", 0, "A")

    def second_item() -> Generator[simpy.Event, object]:
        yield from h.sender.plmm.reserve(h.env, second, SIZE_GB, EPS)
        h.ledger.mark_complete(second)

    h.env.process(second_item())
    h.start()
    h.start(PlannedTransfer("R2", 0, "A", "B", start_s=12.0, end_s=14.0))
    h.env.run()
    assert h.violations == []
    assert h.results == [True, True]
    assert h.ended_at == [15.0, 17.0]


def test_a_link_not_visible_at_the_start_is_a_violation() -> None:
    h = harness(visible(Window(20.0, 30.0)))
    h.data_on_sender_at(0.0)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.LINK_WINDOW]
    assert h.violations[0].at_s == 10.0
    assert h.link.channel.count == 0


def test_a_full_plmm_on_the_receiver_is_a_violation_there() -> None:
    h = harness()
    h.data_on_sender_at(0.0)
    assert h.receiver is not None
    receiver = h.receiver

    def fill() -> Generator[simpy.Event, object]:
        yield from receiver.plmm.reserve(h.env, DataKey("X", 0, "B"), 10.0, EPS)

    h.env.process(fill())
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [(v.kind, v.node) for v in h.violations] == [(ViolationKind.PLMM_FULL, "B")]
    assert h.violations[0].at_s == pytest.approx(10.5 + EPS)
    assert h.link.channel.count == 0
    assert not h.ledger.is_complete(ON_RECEIVER)


def test_a_transfer_to_the_ground_station_delivers_the_item() -> None:
    env = simpy.Environment()
    link = Link("A", "GS", 2.0, 0.5, AlwaysAvailable())
    h = Harness(
        env,
        DataLedger(env),
        satellite("A", env),
        None,
        LinkRuntime(env, link, "A", "GS", EPS),
    )
    h.data_on_sender_at(0.0)
    h.start(PlannedTransfer("R1", 0, "A", "GS", start_s=10.0, end_s=12.0))
    h.env.run()
    assert h.results == [True]
    assert h.ended_at == [12.5]
    assert h.ledger.is_complete(DataKey("R1", 0, "GS"))
    assert h.sender.plmm.level_gb == 0.0
