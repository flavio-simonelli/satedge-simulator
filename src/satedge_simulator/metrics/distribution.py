"""Summary of a sample of durations: count, mean, median, 95th percentile and maximum."""

from __future__ import annotations

import statistics
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Distribution:
    """A sample of durations in seconds, summarised. All values are ``None`` on an empty sample.

    The percentiles interpolate linearly between the order statistics, as the ``inclusive``
    method of :func:`statistics.quantiles` does.
    """

    count: int
    mean: float | None = None
    p50: float | None = None
    p95: float | None = None
    max: float | None = None

    @staticmethod
    def of(values: Iterable[float]) -> Distribution:
        sample = sorted(values)
        if not sample:
            return Distribution(count=0)
        if len(sample) == 1:
            only = sample[0]
            return Distribution(1, only, only, only, only)
        percentiles = statistics.quantiles(sample, n=100, method="inclusive")
        return Distribution(
            count=len(sample),
            mean=statistics.fmean(sample),
            p50=statistics.median(sample),
            p95=percentiles[94],
            max=sample[-1],
        )
