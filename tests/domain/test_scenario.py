"""Tests of the scenario and of its simulation settings."""

import pytest

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.domain.scenario import Scenario, SimulationSettings
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
)
from satedge_simulator.domain.workload import Priority, RequestSpec, TaskSpec
from satedge_simulator.errors import ScenarioError


def constellation() -> Constellation:
    sat = Satellite("A", 100.0, 1.0, WindowSet())
    return Constellation(
        [Plane(1, (sat,), com="A")],
        GroundStation("GS"),
        [Link("A", "GS", 1.0, 0.015, AlwaysAvailable())],
    )


def request(origin: str) -> RequestSpec:
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
    with pytest.raises(ScenarioError):
        SimulationSettings(end_s=0.0)
    with pytest.raises(ScenarioError):
        SimulationSettings(end_s=10.0, tolerance_s=-1.0)


def test_request_origin_must_be_a_satellite() -> None:
    with pytest.raises(ScenarioError, match="non è un satellite"):
        Scenario(constellation(), (request("GS"),), SimulationSettings(end_s=10.0))


def test_lead_time_must_be_positive_when_given() -> None:
    with pytest.raises(ScenarioError):
        Scenario(constellation(), (), SimulationSettings(end_s=10.0), lead_time_s=0.0)


def test_valid_scenario_keeps_its_parts() -> None:
    scenario = Scenario(
        constellation(), (request("A"),), SimulationSettings(end_s=10.0)
    )
    assert scenario.lead_time_s is None
    assert scenario.requests[0].origin == "A"
