"""Tests of the violations of the plan."""

import pytest

from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.errors import StateError


def test_a_violation_records_its_reason_and_place() -> None:
    violation = Violation(12.5, ViolationKind.HPC_WINDOW, "R1", "P1-S3")
    assert violation.kind == "hpc_window"
    assert violation.node == "P1-S3"


def test_violation_instant_must_be_valid() -> None:
    with pytest.raises(StateError):
        Violation(-1.0, ViolationKind.DATA_NOT_READY, "R1", "A")
