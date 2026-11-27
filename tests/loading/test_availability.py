"""Tests of the expansion of the availability documents into windows."""

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import DomainError
from satedge_simulator.io.availability import PeriodicDoc, WindowDoc, WindowsDoc
from satedge_simulator.loading.availability import explicit_windows, periodic_windows


def periodic(**changes: float) -> PeriodicDoc:
    fields: dict[str, float] = {
        "period_s": 100.0,
        "duration_s": 20.0,
        "first_start_s": 5.0,
    }
    fields.update(changes)
    return PeriodicDoc(kind="periodic", **fields)  # type: ignore[arg-type]


def test_periodic_windows_open_every_period_before_the_horizon() -> None:
    windows = periodic_windows(periodic(), horizon_s=250.0)
    assert [(w.start, w.end) for w in windows.windows] == [
        (5.0, 25.0),
        (105.0, 125.0),
        (205.0, 225.0),
    ]


def test_a_window_opening_at_the_horizon_is_left_out() -> None:
    windows = periodic_windows(
        periodic(first_start_s=0.0, duration_s=10.0), horizon_s=200.0
    )
    assert [w.start for w in windows.windows] == [0.0, 100.0]


def test_a_duration_not_below_the_period_is_rejected() -> None:
    with pytest.raises(DomainError):
        periodic_windows(periodic(duration_s=100.0), horizon_s=1000.0)


def test_explicit_windows_are_put_in_time_order() -> None:
    doc = WindowsDoc(
        kind="windows",
        windows=[
            WindowDoc(start_s=30.0, end_s=40.0),
            WindowDoc(start_s=0.0, end_s=10.0),
        ],
    )
    assert explicit_windows(doc) == WindowSet((Window(0.0, 10.0), Window(30.0, 40.0)))
