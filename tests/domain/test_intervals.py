"""Tests of the windows of time."""

import math

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import DomainError


def test_window_rejects_invalid_bounds() -> None:
    with pytest.raises(DomainError):
        Window(-1.0, 5.0)
    with pytest.raises(DomainError):
        Window(5.0, 5.0)
    with pytest.raises(DomainError):
        Window(0.0, math.inf)


def test_window_contains_and_covers_with_tolerance() -> None:
    w = Window(10.0, 20.0)
    assert w.contains(10.0)
    assert not w.contains(20.1)
    assert w.contains(20.1, eps=0.2)
    assert w.covers(12.0, 18.0)
    assert not w.covers(12.0, 20.5)
    assert w.covers(12.0, 20.5, eps=0.5)


def test_window_set_keeps_its_windows_in_order() -> None:
    windows = WindowSet((Window(0.0, 10.0), Window(20.0, 30.0)))
    assert windows.windows == (Window(0.0, 10.0), Window(20.0, 30.0))


def test_window_set_accepts_a_list_and_keeps_a_tuple() -> None:
    windows = WindowSet([Window(0.0, 10.0)])
    assert windows.windows == (Window(0.0, 10.0),)


def test_window_set_rejects_unordered_overlapping_or_touching_windows() -> None:
    with pytest.raises(DomainError):
        WindowSet((Window(30.0, 40.0), Window(0.0, 10.0)))
    with pytest.raises(DomainError):
        WindowSet((Window(0.0, 10.0), Window(10.0, 20.0)))
    with pytest.raises(DomainError):
        WindowSet((Window(0.0, 10.0), Window(5.0, 20.0)))


def test_window_set_is_a_value() -> None:
    assert WindowSet((Window(0.0, 1.0),)) == WindowSet([Window(0.0, 1.0)])
    assert WindowSet() != WindowSet((Window(0.0, 1.0),))
    with pytest.raises(AttributeError):
        WindowSet().windows = ()  # type: ignore[misc]
