"""Tests of the summary of a sample."""

from satedge_simulator.metrics.distribution import Distribution


def test_an_empty_sample_has_no_values() -> None:
    assert Distribution.of([]) == Distribution(count=0)


def test_a_single_value_is_every_statistic() -> None:
    assert Distribution.of([7.0]) == Distribution(1, 7.0, 7.0, 7.0, 7.0)


def test_the_percentiles_interpolate_between_order_statistics() -> None:
    summary = Distribution.of(float(v) for v in range(100, -1, -1))  # 0..100, unsorted
    assert summary == Distribution(101, 50.0, 50.0, 95.0, 100.0)
