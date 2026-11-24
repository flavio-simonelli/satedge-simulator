"""Tests of the propagation of the plan, on small networks whose arrival instants are known."""

import math

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.errors import ScenarioError
from satedge_simulator.planning.propagation import plan_arrival_times

LATENCY = 0.015


def sat(node: str) -> Satellite:
    return Satellite(node, 100.0, 1.0, WindowSet())


def windows(*spans: tuple[float, float]) -> WindowedAvailability:
    return WindowedAvailability(WindowSet(Window(a, b) for a, b in spans))


def network(ground_links: list[Link], inter: Link | None = None) -> Constellation:
    """Two planes of two satellites each, plus an isolated plane of one."""
    planes = [
        Plane(1, (sat("COM1"), sat("P1-S1")), com="COM1"),
        Plane(2, (sat("COM2"), sat("P2-S1")), com="COM2"),
        Plane(3, (sat("COM3"),), com="COM3"),
    ]
    links = [
        Link("COM1", "P1-S1", 1.0, LATENCY, AlwaysAvailable()),
        Link("COM2", "P2-S1", 1.0, LATENCY, AlwaysAvailable()),
        *ground_links,
    ]
    if inter is not None:
        links.append(inter)
    return Constellation(planes, GroundStation("GS"), links)


def test_the_plan_leaves_when_the_contact_opens() -> None:
    cons = network([Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0)))])
    arrival = plan_arrival_times(cons, ready_at_s=0.0)
    assert arrival["COM1"] == pytest.approx(300.0 + LATENCY)


def test_the_plan_is_relayed_over_always_available_links() -> None:
    cons = network([Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0)))])
    arrival = plan_arrival_times(cons, ready_at_s=0.0)
    assert arrival["P1-S1"] == pytest.approx(300.0 + 2 * LATENCY)


def test_the_plan_waits_at_a_com_for_the_next_contact() -> None:
    """The direct contact with COM2 is closed: the plan waits at COM1 for COM1-COM2."""
    inter = Link("COM1", "COM2", 1.0, LATENCY, windows((600.0, 1200.0)))
    cons = network([Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0)))], inter)
    arrival = plan_arrival_times(cons, ready_at_s=0.0)
    assert arrival["COM2"] == pytest.approx(600.0 + LATENCY)
    assert arrival["P2-S1"] == pytest.approx(600.0 + 2 * LATENCY)


def test_the_earliest_route_is_taken() -> None:
    """A direct contact with COM2 that opens first beats the route through COM1."""
    inter = Link("COM1", "COM2", 1.0, LATENCY, windows((600.0, 1200.0)))
    cons = network(
        [
            Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0))),
            Link("COM2", "GS", 1.0, LATENCY, windows((100.0, 200.0))),
        ],
        inter,
    )
    assert plan_arrival_times(cons, 0.0)["COM2"] == pytest.approx(100.0 + LATENCY)


def test_a_window_that_closes_before_the_plan_is_ready_is_unusable() -> None:
    cons = network([Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0)))])
    assert math.isinf(plan_arrival_times(cons, ready_at_s=399.99)["COM1"])


def test_a_satellite_without_links_is_unreachable() -> None:
    cons = network([Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0)))])
    assert math.isinf(plan_arrival_times(cons, 0.0)["COM3"])


def test_the_result_has_one_entry_per_satellite_only() -> None:
    cons = network([Link("COM1", "GS", 1.0, LATENCY, windows((300.0, 400.0)))])
    assert set(plan_arrival_times(cons, 0.0)) == {
        "COM1",
        "P1-S1",
        "COM2",
        "P2-S1",
        "COM3",
    }


def test_the_ready_instant_must_be_valid() -> None:
    cons = network([])
    with pytest.raises(ScenarioError):
        plan_arrival_times(cons, -1.0)
    with pytest.raises(ScenarioError):
        plan_arrival_times(cons, math.inf)
