"""Tests of the runtime of one direction of a link."""

import pytest
import simpy

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Link,
    WindowedAvailability,
)
from satedge_simulator.errors import StateError
from satedge_simulator.runtime.links import LinkRuntime

EPS = 1e-4


def test_a_direction_must_join_the_endpoints_of_the_link() -> None:
    env = simpy.Environment()
    link = Link("A", "B", 1.0, 0.1, AlwaysAvailable())
    with pytest.raises(StateError, match="non collega"):
        LinkRuntime(env, link, "A", "C", EPS)


def test_a_link_always_available_never_closes() -> None:
    env = simpy.Environment()
    link = LinkRuntime(env, Link("A", "B", 1.0, 0.1, AlwaysAvailable()), "A", "B", EPS)
    closing = link.window_closing()
    assert closing is not None
    env.run(until=1e6)
    assert not closing.triggered


def test_a_windowed_link_closes_at_the_end_of_its_window_plus_the_tolerance() -> None:
    env = simpy.Environment()
    availability = WindowedAvailability(WindowSet([Window(0.0, 100.0)]))
    link = LinkRuntime(env, Link("A", "B", 1.0, 0.1, availability), "B", "A", EPS)
    closing = link.window_closing()
    assert closing is not None
    env.run(until=closing)
    assert env.now == pytest.approx(100.0 + EPS)
    env.run(until=101.0)
    assert link.window_closing() is None
