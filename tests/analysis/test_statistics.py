"""Tests of the estimators: Welford, confidence intervals, autocorrelation, Welch."""

import statistics

import pytest

from satedge_simulator.analysis.autocorrelation import autocorrelation
from satedge_simulator.analysis.statistics import Welford, confidence_interval
from satedge_simulator.analysis.welch import welch_moving_average
from satedge_simulator.errors import ScenarioError


def test_welford_matches_the_two_pass_estimates() -> None:
    values = [3.0, 1.5, 4.25, 9.0, 2.0, 6.5]
    w = Welford()
    for x in values:
        w.add(x)
    assert w.count == 6
    assert w.mean == pytest.approx(statistics.fmean(values))
    assert w.variance == pytest.approx(statistics.variance(values))


def test_the_interval_uses_students_t_on_the_sample_deviation() -> None:
    ci = confidence_interval([1.0, 2.0, 3.0, 4.0, 5.0], level=0.95)
    assert ci is not None
    # t(4, 0.975) = 2.776445, s = sqrt(2.5), n = 5
    assert ci.mean == 3.0
    half = 2.776445 * 2.5**0.5 / 5**0.5
    assert ci.half_width == pytest.approx(half, rel=1e-6)
    assert (ci.low, ci.high) == pytest.approx((3.0 - half, 3.0 + half), rel=1e-6)


def test_an_interval_needs_two_values() -> None:
    assert confidence_interval([]) is None
    single = confidence_interval([7.0])
    assert single is not None
    assert single.half_width is None
    assert single.low is None
    with pytest.raises(ScenarioError, match="livello"):
        confidence_interval([1.0, 2.0], level=1.0)


def test_an_alternating_series_is_negatively_correlated_at_lag_one() -> None:
    series = [1.0, -1.0] * 50
    r = autocorrelation(series, 2)
    assert r[0] == pytest.approx(-99 / 100)
    assert r[1] == pytest.approx(98 / 100)


def test_a_constant_series_has_no_autocorrelation() -> None:
    assert autocorrelation([4.0] * 10, 3) == (0.0, 0.0, 0.0)


def test_a_constant_series_whose_mean_rounds_has_no_autocorrelation() -> None:
    # sum([0.1] * 3) / 3 is 0.10000000000000002: the centred values are not all zero.
    assert autocorrelation([0.1] * 3, 2) == (0.0, 0.0)


def test_the_lag_must_fit_in_the_series() -> None:
    with pytest.raises(ScenarioError, match="lag"):
        autocorrelation([1.0, 2.0, 3.0], 3)


def test_welch_averages_symmetric_windows_that_grow_at_the_start() -> None:
    series = [
        float(v) for v in range(1, 10)
    ]  # 1 … 9: the moving average of a line is the line
    assert welch_moving_average(series, 2) == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0)
    with pytest.raises(ScenarioError, match="Welch"):
        welch_moving_average(series, 5)
