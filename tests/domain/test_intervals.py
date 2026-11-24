"""Tests of the windows of time."""

import math

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import ScenarioError


def test_window_rejects_invalid_bounds() -> None:
    with pytest.raises(ScenarioError):
        Window(-1.0, 5.0)
    with pytest.raises(ScenarioError):
        Window(5.0, 5.0)
    with pytest.raises(ScenarioError):
        Window(0.0, math.inf)


def test_window_contains_and_covers_with_tolerance() -> None:
    w = Window(10.0, 20.0)
    assert w.contains(10.0)
    assert not w.contains(20.1)
    assert w.contains(20.1, eps=0.2)
    assert w.covers(12.0, 18.0)
    assert not w.covers(12.0, 20.5)
    assert w.covers(12.0, 20.5, eps=0.5)


def test_window_clipped_duration() -> None:
    w = Window(10.0, 20.0)
    assert w.clipped(5.0) == 0.0
    assert w.clipped(15.0) == 5.0
    assert w.clipped(math.inf) == 10.0


def test_window_set_sorts_and_rejects_overlap_or_touch() -> None:
    ws = WindowSet([Window(30.0, 40.0), Window(0.0, 10.0)])
    assert [w.start for w in ws] == [0.0, 30.0]
    with pytest.raises(ScenarioError):
        WindowSet([Window(0.0, 10.0), Window(10.0, 20.0)])
    with pytest.raises(ScenarioError):
        WindowSet([Window(0.0, 10.0), Window(5.0, 20.0)])


def test_window_set_containing() -> None:
    ws = WindowSet([Window(0.0, 10.0), Window(20.0, 30.0)])
    assert ws.containing(5.0) == Window(0.0, 10.0)
    assert ws.containing(15.0) is None
    assert ws.containing(10.5, eps=0.5) == Window(0.0, 10.0)
    assert ws.containing(-1.0) is None


def test_earliest_fit_waits_for_a_window_that_holds_the_span() -> None:
    ws = WindowSet([Window(0.0, 10.0), Window(20.0, 30.0)])
    assert ws.earliest_fit(0.0, 5.0) == 0.0
    assert ws.earliest_fit(6.0, 4.0) == 6.0
    # 6 s from 6 do not fit before 10: the second window is used
    assert ws.earliest_fit(6.0, 6.0) == 20.0
    assert ws.earliest_fit(0.0, 11.0) is None
    assert ws.earliest_fit(31.0, 1.0) is None


def test_total_duration_before_an_instant() -> None:
    ws = WindowSet([Window(0.0, 10.0), Window(20.0, 30.0)])
    assert ws.total_duration() == 20.0
    assert ws.total_duration(until=25.0) == 15.0


def test_window_set_equality() -> None:
    assert WindowSet([Window(0.0, 1.0)]) == WindowSet([Window(0.0, 1.0)])
    assert WindowSet() != WindowSet([Window(0.0, 1.0)])
