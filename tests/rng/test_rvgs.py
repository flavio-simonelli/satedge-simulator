"""Tests of the random variate generators: exact values on scripted uniforms, moments on many
draws of a real stream."""

import statistics
from collections.abc import Iterator

import pytest

from satedge_simulator.errors import ScenarioError
from satedge_simulator.rng.rngs import MultiStreamRng
from satedge_simulator.rng.rvgs import (
    balanced_hyperexponential,
    bernoulli,
    equilikely,
    exponential,
    hyperexponential,
    normal,
    poisson,
    uniform,
)


class Scripted:
    """A source that returns the given uniforms, in order."""

    def __init__(self, *values: float) -> None:
        self._values: Iterator[float] = iter(values)

    def random(self) -> float:
        return next(self._values)


def test_inversion_on_given_uniforms() -> None:
    assert uniform(Scripted(0.25), 2.0, 12.0) == 4.5
    assert equilikely(Scripted(0.0), 1, 3) == 1
    assert equilikely(Scripted(0.999), 1, 3) == 3
    assert bernoulli(Scripted(0.69), 0.3) == 0
    assert bernoulli(Scripted(0.71), 0.3) == 1
    assert exponential(Scripted(0.5), 2.0) == pytest.approx(2.0 * 0.6931471805599453)


def test_the_hyperexponential_draws_branch_and_value_from_the_same_source() -> None:
    # 0.95 >= 1 - p picks the first branch, then the exponential uses 0.5
    value = hyperexponential(Scripted(0.95, 0.5), 0.1, 10.0, 1.0)
    assert value == pytest.approx(10.0 * 0.6931471805599453)


def test_balanced_means_split_the_mean_in_two_halves() -> None:
    p, m1, m2 = balanced_hyperexponential(mean=4.0, cv=4.0)
    assert p * m1 == pytest.approx(2.0)
    assert (1 - p) * m2 == pytest.approx(2.0)
    # the second moment of a hyperexponential gives back the coefficient of variation
    second = 2 * (p * m1**2 + (1 - p) * m2**2)
    assert (second - 4.0**2) ** 0.5 / 4.0 == pytest.approx(4.0)


@pytest.mark.parametrize(
    ("draw", "mean", "variance"),
    [
        (lambda s: exponential(s, 2.0), 2.0, 4.0),
        (lambda s: uniform(s, 2.0, 12.0), 7.0, 100 / 12),
        (lambda s: normal(s, 1.0, 2.0), 1.0, 4.0),
        (lambda s: float(poisson(s, 3.0)), 3.0, 3.0),
        (lambda s: float(equilikely(s, 1, 3)), 2.0, 2 / 3),
    ],
)
def test_the_moments_of_many_draws(draw, mean: float, variance: float) -> None:  # type: ignore[no-untyped-def]
    stream = MultiStreamRng(123_456_789).stream(3)
    sample = [draw(stream) for _ in range(50_000)]
    assert statistics.fmean(sample) == pytest.approx(mean, rel=0.03)
    assert statistics.variance(sample) == pytest.approx(variance, rel=0.05)


def test_the_hyperexponential_mean_on_many_draws() -> None:
    stream = MultiStreamRng(123_456_789).stream(9)
    p, m1, m2 = balanced_hyperexponential(mean=4.0, cv=2.0)
    sample = [hyperexponential(stream, p, m1, m2) for _ in range(100_000)]
    assert statistics.fmean(sample) == pytest.approx(4.0, rel=0.03)


def test_invalid_parameters_are_scenario_errors() -> None:
    with pytest.raises(ScenarioError, match="Exponential"):
        exponential(Scripted(0.5), 0.0)
    with pytest.raises(ScenarioError, match="Uniform"):
        uniform(Scripted(0.5), 3.0, 3.0)
    with pytest.raises(ScenarioError, match="coefficiente di variazione"):
        balanced_hyperexponential(1.0, 1.0)
