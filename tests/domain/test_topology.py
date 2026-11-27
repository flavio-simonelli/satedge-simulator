"""Tests of the nodes, the links and the validation of the constellation."""

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
from satedge_simulator.errors import DomainError

NO_WINDOWS = WindowSet()


def sat(node: str) -> Satellite:
    return Satellite(
        node, plmm_capacity_gb=100.0, hpc_rate_gbps=1.0, hpc_windows=NO_WINDOWS
    )


def test_satellite_io_time_is_size_over_rate() -> None:
    fast = Satellite("S", 100.0, hpc_rate_gbps=2.0, hpc_windows=NO_WINDOWS)
    assert fast.hpc_io_time(8.0) == 4.0


def test_satellite_rejects_non_positive_capacity() -> None:
    with pytest.raises(DomainError):
        Satellite("S", plmm_capacity_gb=0.0, hpc_rate_gbps=1.0, hpc_windows=NO_WINDOWS)


def test_link_rejects_self_loop_and_bad_parameters() -> None:
    with pytest.raises(DomainError):
        Link("A", "A", 1.0, 0.015, AlwaysAvailable())
    with pytest.raises(DomainError):
        Link("A", "B", 0.0, 0.015, AlwaysAvailable())
    with pytest.raises(DomainError):
        Link("A", "B", 1.0, -1.0, AlwaysAvailable())


def test_link_is_symmetric_and_knows_its_availability() -> None:
    always = Link("A", "B", 1.0, 0.015, AlwaysAvailable())
    windowed = Link(
        "A", "GS", 1.0, 0.015, WindowedAvailability(WindowSet([Window(0.0, 10.0)]))
    )
    assert always.connects("B", "A")
    assert not always.is_windowed
    assert windowed.is_windowed
    assert always.transmission_time(4.0) == 4.0


def test_plane_com_must_be_one_of_its_satellites() -> None:
    satellites = (sat("A"),)
    with pytest.raises(DomainError):
        Plane(1, satellites, com="B")


def test_constellation_rejects_unknown_link_endpoint() -> None:
    plane = Plane(1, (sat("A"), sat("B")), com="A")
    ground = GroundStation("GS")
    to_unknown = Link("A", "X", 1.0, 0.015, AlwaysAvailable())
    with pytest.raises(DomainError):
        Constellation([plane], ground, [to_unknown])


def test_constellation_rejects_duplicate_link_in_either_order() -> None:
    plane = Plane(1, (sat("A"), sat("B")), com="A")
    links = [
        Link("A", "B", 1.0, 0.015, AlwaysAvailable()),
        Link("B", "A", 1.0, 0.015, AlwaysAvailable()),
    ]
    with pytest.raises(DomainError):
        Constellation([plane], GroundStation("GS"), links)


def test_constellation_rejects_ground_station_that_is_a_satellite() -> None:
    plane = Plane(1, (sat("A"),), com="A")
    with pytest.raises(DomainError):
        Constellation([plane], GroundStation("A"), [])


def test_constellation_lookups() -> None:
    plane = Plane(1, (sat("A"), sat("B")), com="A")
    link = Link("A", "B", 1.0, 0.015, AlwaysAvailable())
    constellation = Constellation([plane], GroundStation("GS"), [link])
    assert constellation.satellite("B").id == "B"
    assert constellation.is_satellite("A")
    assert not constellation.is_satellite("GS")
    assert constellation.link_between("B", "A") == link
    assert constellation.link_between("A", "GS") is None
    with pytest.raises(DomainError):
        constellation.satellite("GS")
