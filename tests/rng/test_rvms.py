"""Tests of the distribution functions, with the values the original library verified."""

import pytest

from satedge_simulator.errors import ScenarioError
from satedge_simulator.rng.rvms import (
    cdf_standard,
    cdf_student,
    idf_normal,
    idf_standard,
    idf_student,
)


@pytest.mark.parametrize(
    ("n", "u", "expected"),
    [(10, 0.8, 0.879058), (10, 0.975, 2.228139), (100, 0.975, 1.983972)],
)
def test_student_quantiles_match_the_original_library(
    n: int, u: float, expected: float
) -> None:
    assert idf_student(n, u) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize(
    ("m", "s", "u", "expected"),
    [(9.0, 2.0, 0.66, 9.824926), (-19.0, 3.4, 0.81, -16.015153)],
)
def test_normal_quantiles_match_the_original_library(
    m: float, s: float, u: float, expected: float
) -> None:
    assert idf_normal(m, s, u) == pytest.approx(expected, abs=1e-6)


def test_the_quantile_inverts_the_distribution_function() -> None:
    assert cdf_student(10, idf_student(10, 0.95)) == pytest.approx(0.95, abs=1e-9)
    assert cdf_standard(idf_standard(0.975)) == pytest.approx(0.975, abs=1e-9)
    assert idf_standard(0.975) == pytest.approx(1.959964, abs=1e-6)


def test_student_tends_to_the_normal() -> None:
    assert idf_student(100_000, 0.975) == pytest.approx(idf_standard(0.975), abs=1e-4)


def test_the_quantile_needs_a_probability_and_degrees_of_freedom() -> None:
    with pytest.raises(ScenarioError):
        idf_student(10, 1.0)
    with pytest.raises(ScenarioError):
        idf_student(0, 0.5)
