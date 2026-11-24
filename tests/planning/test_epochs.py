"""Tests of the planning epochs, on a small constellation with two communication satellites."""

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
from satedge_simulator.planning.epochs import contact_openings, planning_epochs


def constellation(
    com1_gs: list[tuple[float, float]], com2_gs: list[tuple[float, float]]
) -> Constellation:
    def sat(node: str) -> Satellite:
        return Satellite(node, 100.0, 1.0, WindowSet())

    def windows(spans: list[tuple[float, float]]) -> WindowedAvailability:
        return WindowedAvailability(WindowSet(Window(a, b) for a, b in spans))

    planes = [Plane(1, (sat("COM1"),), "COM1"), Plane(2, (sat("COM2"),), "COM2")]
    links = [
        Link("COM1", "COM2", 1.0, 0.015, AlwaysAvailable()),
        Link("COM1", "GS", 1.0, 0.015, windows(com1_gs)),
        Link("COM2", "GS", 1.0, 0.015, windows(com2_gs)),
    ]
    return Constellation(planes, GroundStation("GS"), links)


def test_openings_of_the_ground_links_only() -> None:
    cons = constellation([(300.0, 400.0), (900.0, 1000.0)], [(500.0, 600.0)])
    assert contact_openings(cons) == (300.0, 500.0, 900.0)


def test_one_epoch_per_opening_starts_the_lead_time_before() -> None:
    cons = constellation([(300.0, 400.0)], [(500.0, 600.0)])
    epochs = planning_epochs(cons, lead_time_s=100.0, end_s=1000.0)
    assert [(e.start_s, e.ready_s) for e in epochs] == [(200.0, 300.0), (400.0, 500.0)]
    assert [e.index for e in epochs] == [0, 1]
    assert epochs[0].lead_time_s == pytest.approx(100.0)


def test_coincident_openings_share_one_epoch() -> None:
    cons = constellation([(300.0, 400.0)], [(300.0, 350.0)])
    assert len(planning_epochs(cons, lead_time_s=100.0, end_s=1000.0)) == 1


def test_an_opening_too_early_has_no_epoch() -> None:
    cons = constellation([(50.0, 100.0), (300.0, 400.0)], [])
    epochs = planning_epochs(cons, lead_time_s=100.0, end_s=1000.0)
    assert [e.ready_s for e in epochs] == [300.0]


def test_epochs_starting_at_or_after_the_end_are_not_generated() -> None:
    cons = constellation([(300.0, 400.0), (900.0, 1000.0)], [])
    epochs = planning_epochs(cons, lead_time_s=100.0, end_s=800.0)
    assert [e.ready_s for e in epochs] == [300.0]


def test_lead_time_and_end_must_be_positive() -> None:
    cons = constellation([(300.0, 400.0)], [])
    with pytest.raises(ScenarioError):
        planning_epochs(cons, lead_time_s=0.0, end_s=10.0)
    with pytest.raises(ScenarioError):
        planning_epochs(cons, lead_time_s=10.0, end_s=math.inf)
