"""Infinite horizon: the method of the batch means on one long run.

The warm-up is discarded, then the rest of the run is cut into batches, and the interval
estimate is computed on the batch means, which are about independent when the batches are long
enough, never on the observations inside a batch, which are correlated. The lag-1
autocorrelation of the batch means tells whether they are: below about 0.2 they can be taken as
independent, otherwise the batches must be longer.

A per-request statistic is batched by requests, ``b`` consecutive observations per batch. A
statistic over time is batched by time; the computing windows and the contacts repeat with the
orbital period, so a batch should last a whole number of periods, or each batch would see a
different phase of the orbit.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from satedge_simulator.analysis.autocorrelation import autocorrelation
from satedge_simulator.analysis.observations import RunObservations, Statistic
from satedge_simulator.analysis.run import observe
from satedge_simulator.analysis.statistics import (
    ConfidenceInterval,
    confidence_interval,
)
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.errors import InputError
from satedge_simulator.planning.ports import Planner
from satedge_simulator.rng.rngs import MultiStreamRng


@dataclass(frozen=True, slots=True)
class Batches:
    """The batch means of one statistic and their interval estimate.

    Attributes:
        means: The mean of each batch, in time order.
        interval: The interval estimate over the batch means; ``None`` without batches.
        lag1: The lag-1 autocorrelation of the batch means; ``None`` below three batches.
    """

    means: tuple[float, ...]
    interval: ConfidenceInterval | None
    lag1: float | None


@dataclass(frozen=True, slots=True)
class BatchMeansReport:
    """The estimates of an infinite-horizon study.

    Attributes:
        warmup_s: The part of the run discarded.
        end_s: The end of the run.
        batch_size: Observations per batch, for the per-request statistics.
        batch_duration_s: Seconds per batch, for the statistics over time.
        level: The confidence level.
        results: The batches of each statistic.
    """

    warmup_s: float
    end_s: float
    batch_size: int
    batch_duration_s: float
    level: float
    results: Mapping[Statistic, Batches]


def batch_means(
    scenario: Scenario,
    planner: Planner,
    warmup_s: float,
    batch_size: int,
    batch_duration_s: float,
    level: float = 0.95,
    lead_time_s: float | None = None,
) -> BatchMeansReport:
    """Run ``scenario`` once, to its end, and estimate each statistic by batch means.

    Raises:
        InputError: If the warm-up is not before the end, or a batch is empty.
    """
    end_s = scenario.settings.end_s
    if not 0.0 <= warmup_s < end_s:
        raise InputError(
            f"il riscaldamento deve essere tra 0 e la fine della simulazione, invece è {warmup_s}"
        )
    if batch_size < 1 or batch_duration_s <= 0:
        raise InputError("la dimensione e la durata dei batch devono essere > 0")
    run = observe(
        scenario, planner, MultiStreamRng(scenario.settings.seed), lead_time_s
    )
    results = {
        s: _summarise(
            _by_requests(run.observations, s, warmup_s, batch_size)
            if s.per_request
            else _by_time(run.observations, s, warmup_s, end_s, batch_duration_s),
            level,
        )
        for s in Statistic
    }
    return BatchMeansReport(
        warmup_s, end_s, batch_size, batch_duration_s, level, MappingProxyType(results)
    )


def _by_requests(
    run: RunObservations, statistic: Statistic, warmup_s: float, size: int
) -> list[float]:
    """The means of the full batches of ``size`` observations after the warm-up."""
    values = [o.value for o in run.observations(statistic) if o.time_s >= warmup_s]
    full = len(values) // size
    return [sum(values[k * size : (k + 1) * size]) / size for k in range(full)]


def _by_time(
    run: RunObservations,
    statistic: Statistic,
    warmup_s: float,
    end_s: float,
    duration_s: float,
) -> list[float]:
    """The time averages of the whole batches of ``duration_s`` after the warm-up."""
    means = []
    start = warmup_s
    while start + duration_s <= end_s:
        mean = run.mean(statistic, start, start + duration_s)
        if mean is not None:
            means.append(mean)
        start += duration_s
    return means


def _summarise(means: list[float], level: float) -> Batches:
    lag1 = autocorrelation(means, 1)[0] if len(means) >= 3 else None
    return Batches(tuple(means), confidence_interval(means, level), lag1)
