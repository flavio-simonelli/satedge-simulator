"""Point and interval estimates of a mean from a sample of independent observations."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from satedge_simulator.errors import ScenarioError
from satedge_simulator.rng.rvms import idf_student


class Welford:
    """Running mean and variance of a sample, in one pass and without cancellation (Welford)."""

    __slots__ = ("_count", "_mean", "_sum_squares")

    def __init__(self) -> None:
        self._count = 0
        self._mean = 0.0
        self._sum_squares = 0.0

    def add(self, x: float) -> None:
        self._count += 1
        delta = x - self._mean
        self._mean += delta / self._count
        self._sum_squares += delta * (x - self._mean)

    @property
    def count(self) -> int:
        return self._count

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def variance(self) -> float:
        """The sample variance, with ``n − 1`` in the denominator; 0 below two observations."""
        return self._sum_squares / (self._count - 1) if self._count > 1 else 0.0

    @property
    def stdev(self) -> float:
        return math.sqrt(self.variance)


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """An interval estimate of a mean: ``mean ± half_width`` at the given level.

    Attributes:
        mean: The sample mean.
        half_width: ``t(n − 1, 1 − α/2) · s / √n``; ``None`` below two observations.
        count: The number of observations.
        level: The confidence level, ``1 − α``.
    """

    mean: float
    half_width: float | None
    count: int
    level: float

    @property
    def low(self) -> float | None:
        return None if self.half_width is None else self.mean - self.half_width

    @property
    def high(self) -> float | None:
        return None if self.half_width is None else self.mean + self.half_width


def confidence_interval(
    values: Iterable[float], level: float = 0.95
) -> ConfidenceInterval | None:
    """The interval estimate of the mean of independent, identically distributed ``values``.

    The values must be independent: the means of the replications, or the means of batches
    long enough to be uncorrelated, never the observations of one run, which are correlated.

    Returns:
        ``None`` for an empty sample.

    Raises:
        ScenarioError: If the level is not between 0 and 1.
    """
    if not 0.0 < level < 1.0:
        raise ScenarioError(
            f"il livello di confidenza deve essere tra 0 e 1, invece è {level}"
        )
    w = Welford()
    for x in values:
        w.add(x)
    if w.count == 0:
        return None
    if w.count == 1:
        return ConfidenceInterval(w.mean, None, 1, level)
    t = idf_student(w.count - 1, 1.0 - (1.0 - level) / 2.0)
    return ConfidenceInterval(w.mean, t * w.stdev / math.sqrt(w.count), w.count, level)
