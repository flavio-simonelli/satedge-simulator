"""Tests of the PLMM on SimPy: capacity, timeout of a reservation, release at the same instant."""

from collections.abc import Generator

import pytest
import simpy

from satedge_simulator.errors import StateError
from satedge_simulator.runtime.ledger import DataKey
from satedge_simulator.runtime.plmm import Plmm

EPS = 1e-4
A = DataKey("R1", 0, "A")
B = DataKey("R2", 0, "A")


def test_reservation_within_capacity_is_stored_at_once() -> None:
    env = simpy.Environment()
    plmm = Plmm(env, capacity_gb=10.0)
    results: list[bool] = []

    def process() -> Generator[simpy.Event, object]:
        results.append((yield from plmm.reserve(env, A, 4.0, EPS)))

    env.process(process())
    env.run()

    assert results == [True]
    assert plmm.level_gb == pytest.approx(4.0)
    assert plmm.occupied_gb(A) == pytest.approx(4.0)


def test_reservation_that_does_not_fit_times_out_and_stores_nothing() -> None:
    env = simpy.Environment()
    plmm = Plmm(env, capacity_gb=10.0)
    results: list[bool] = []

    def process() -> Generator[simpy.Event, object]:
        yield from plmm.reserve(env, A, 8.0, EPS)
        results.append((yield from plmm.reserve(env, B, 5.0, EPS)))

    env.process(process())
    env.run()

    assert results == [False]
    assert plmm.level_gb == pytest.approx(8.0)
    assert plmm.occupied_gb(B) == 0.0


def test_release_at_the_instant_of_a_waiting_reservation_grants_it() -> None:
    env = simpy.Environment()
    plmm = Plmm(env, capacity_gb=10.0)
    granted_at: list[float] = []

    def holder() -> Generator[simpy.Event, object]:
        yield from plmm.reserve(env, A, 8.0, EPS)
        yield env.timeout(3.0)
        plmm.release(A)

    def waiter() -> Generator[simpy.Event, object]:
        yield env.timeout(1.0)
        if (yield from plmm.reserve(env, B, 5.0, 10.0)):
            granted_at.append(env.now)

    env.process(holder())
    env.process(waiter())
    env.run()

    assert granted_at == [3.0]
    assert plmm.occupied_gb(B) == pytest.approx(5.0)


def test_storing_the_same_item_twice_is_an_error() -> None:
    env = simpy.Environment()
    plmm = Plmm(env, capacity_gb=10.0)

    def process() -> Generator[simpy.Event, object]:
        yield from plmm.reserve(env, A, 1.0, EPS)
        yield from plmm.reserve(env, A, 1.0, EPS)

    env.process(process())
    with pytest.raises(StateError):
        env.run()


def test_releasing_an_item_not_stored_is_a_no_op() -> None:
    env = simpy.Environment()
    plmm = Plmm(env, capacity_gb=10.0)
    plmm.release(A)
    assert plmm.level_gb == 0.0
