"""Tests of the runtime of a satellite: the closing of its computing windows."""

import pytest
import simpy

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.topology import Satellite
from satedge_simulator.runtime.satellite import SatelliteRuntime

EPS = 1e-4
WINDOWS = WindowSet([Window(0.0, 100.0), Window(200.0, 300.0)])


def runtime() -> SatelliteRuntime:
    env = simpy.Environment()
    return SatelliteRuntime(env, Satellite("A", 10.0, 1.0, WINDOWS), EPS)


def test_the_closing_fires_at_the_end_of_the_window_plus_the_tolerance() -> None:
    node = runtime()
    closing = node.window_closing()
    assert closing is not None
    node.env.run(until=closing)
    assert node.env.now == pytest.approx(100.0 + EPS)


def test_executions_in_the_same_window_share_the_closing_event() -> None:
    node = runtime()
    first = node.window_closing()
    node.env.run(until=50.0)
    assert node.window_closing() is first


def test_each_window_has_its_own_closing_event() -> None:
    node = runtime()
    first = node.window_closing()
    node.env.run(until=250.0)
    second = node.window_closing()
    assert second is not None
    assert second is not first


def test_no_closing_outside_the_windows() -> None:
    node = runtime()
    node.env.run(until=150.0)
    assert node.window_closing() is None
