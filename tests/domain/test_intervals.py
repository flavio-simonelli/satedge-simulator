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
    touching = [Window(0.0, 10.0), Window(10.0, 20.0)]
    with pytest.raises(ScenarioError):
        WindowSet(touching)
    overlapping = [Window(0.0, 10.0), Window(5.0, 20.0)]
    with pytest.raises(ScenarioError):
        WindowSet(overlapping)


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
    one, same = WindowSet([Window(0.0, 1.0)]), WindowSet([Window(0.0, 1.0)])
    assert one == same
    assert WindowSet() != WindowSet([Window(0.0, 1.0)])


def test_periodic_windows_open_every_period_before_the_horizon() -> None:
    windows = WindowSet.periodic(
        first_start=5.0, period=100.0, duration=20.0, horizon=250.0
    )
    assert [(w.start, w.end) for w in windows] == [
        (5.0, 25.0),
        (105.0, 125.0),
        (205.0, 225.0),
    ]


def test_a_window_opening_at_the_horizon_is_left_out() -> None:
    windows = WindowSet.periodic(
        first_start=0.0, period=100.0, duration=10.0, horizon=200.0
    )
    assert [w.start for w in windows] == [0.0, 100.0]


@pytest.mark.parametrize(
    ("first", "period", "duration"),
    [(-1.0, 100.0, 10.0), (0.0, 100.0, 100.0), (0.0, 100.0, 0.0)],
)
def test_periodic_windows_need_a_valid_first_start_and_a_duration_below_the_period(
    first: float, period: float, duration: float
) -> None:
    with pytest.raises(ScenarioError):
        WindowSet.periodic(first, period, duration, horizon=1000.0)
