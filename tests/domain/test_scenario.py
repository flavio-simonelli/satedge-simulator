"""Tests of the scenario and of its simulation settings."""

import pytest

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.scenario import Scenario, SimulationSettings
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
)
from satedge_simulator.errors import DomainError

SAT_A = Satellite("A", 100.0, 1.0, WindowSet())
FOREIGN = Satellite("X", 100.0, 1.0, WindowSet())


def constellation() -> Constellation:
    sat = SAT_A
    return Constellation(
        [Plane(1, (sat,), com="A")],
        GroundStation("GS"),
        [Link("A", "GS", 1.0, 0.015, AlwaysAvailable())],
    )


def request(origin: Satellite) -> RequestSpec:
    return RequestSpec(
        id="R1",
        priority=Priority.URGENT,
        origin=origin,
        arrival_s=0.0,
        release_s=0.0,
        deadline_s=100.0,
        raw_size_gb=1.0,
        tasks=(TaskSpec(10.0, 0.1),),
    )


def test_settings_reject_invalid_values() -> None:
    with pytest.raises(DomainError):
        SimulationSettings(end_s=0.0)
    with pytest.raises(DomainError):
        SimulationSettings(end_s=10.0, tolerance_s=-1.0)


def test_request_origin_must_be_a_satellite() -> None:
    the_constellation, from_ground = constellation(), request(FOREIGN)
    settings = SimulationSettings(end_s=10.0)
    with pytest.raises(DomainError, match="non è un satellite"):
        Scenario(the_constellation, (from_ground,), settings)


def test_lead_time_must_be_positive_when_given() -> None:
    the_constellation, settings = constellation(), SimulationSettings(end_s=10.0)
    with pytest.raises(DomainError):
        Scenario(the_constellation, (), settings, lead_time_s=0.0)


def test_valid_scenario_keeps_its_parts() -> None:
    scenario = Scenario(
        constellation(), (request(SAT_A),), SimulationSettings(end_s=10.0)
    )
    assert scenario.lead_time_s is None
    assert scenario.requests[0].origin is SAT_A


def test_the_world_horizon_reaches_the_latest_deadline() -> None:
    from satedge_simulator.domain.scenario import world_horizon_s
    from satedge_simulator.domain.workload_model import WorkloadModel

    assert world_horizon_s(100.0, (), None) == 100.0
    model = WorkloadModel(
        arrivals_per_hour=1.0,
        deadline_after_release_s={
            Priority.URGENT: 7200.0,
            Priority.NON_URGENT: 25200.0,
        },
    )
    assert world_horizon_s(100.0, (), model) == 100.0 + 5640.0 + 25200.0
