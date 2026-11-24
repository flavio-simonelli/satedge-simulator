"""Tests of the contact plan lookup."""

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import ScenarioError
from satedge_simulator.io.contact_plan import ContactPlan


def test_windows_are_found_in_either_order() -> None:
    windows = WindowSet([Window(0.0, 10.0)])
    plan = ContactPlan({("COM1", "GS"): windows})
    assert plan.windows_of("GS", "COM1") == windows


def test_missing_pair_is_an_error() -> None:
    plan = ContactPlan({})
    with pytest.raises(ScenarioError):
        plan.windows_of("COM1", "GS")


def test_pair_declared_twice_in_either_order_is_an_error() -> None:
    windows = WindowSet()
    with pytest.raises(ScenarioError):
        ContactPlan({("A", "B"): windows, ("B", "A"): windows})
