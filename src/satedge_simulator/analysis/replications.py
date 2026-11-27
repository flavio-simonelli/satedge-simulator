"""Finite horizon: independent replications, and the transient seen across them.

Each replication runs the whole horizon from the initial state, on the same generator, so it
goes on where the previous one stopped and the replications are independent. Each one gives one
value per statistic, its mean over the horizon, and the interval estimate is computed on these
values, never on the correlated observations of one run.

The transient is the ensemble mean over the replications, cell by cell of a time grid, with its
interval in each cell, and Welch's moving average over it to see where it settles.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from satedge_simulator.analysis.observations import RunObservations, Statistic
from satedge_simulator.analysis.run import observe
from satedge_simulator.analysis.statistics import (
    ConfidenceInterval,
    confidence_interval,
)
from satedge_simulator.analysis.welch import welch_moving_average
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.errors import InputError
from satedge_simulator.planning.ports import Planner
from satedge_simulator.rng.rngs import MultiStreamRng


@dataclass(frozen=True, slots=True)
class TransientCell:
    """One cell ``[start_s, end_s)`` of the transient of a statistic.

    Attributes:
        interval: The ensemble mean over the replications that observed something in the
            cell, with its interval; ``None`` if none did.
        welch: Welch's moving average at the cell; ``None`` where it is not defined.
    """

    start_s: float
    end_s: float
    interval: ConfidenceInterval | None
    welch: float | None


@dataclass(frozen=True, slots=True)
class ReplicationReport:
    """The estimates of a finite-horizon study.

    Attributes:
        replications: The number of replications.
        seed: The seed the generator was planted from.
        level: The confidence level.
        per_replication: The mean of each statistic in each replication (``None`` when the
            replication observed nothing).
        estimates: The interval estimate of each statistic over the replications.
        transient: The transient of each statistic, cell by cell.
    """

    replications: int
    seed: int
    level: float
    per_replication: Mapping[Statistic, tuple[float | None, ...]]
    estimates: Mapping[Statistic, ConfidenceInterval | None]
    transient: Mapping[Statistic, tuple[TransientCell, ...]]


def replicate(
    scenario: Scenario,
    planner: Planner,
    replications: int,
    cell_s: float,
    welch_window: int,
    level: float = 0.95,
    lead_time_s: float | None = None,
) -> ReplicationReport:
    """Run ``replications`` independent replications of ``scenario`` and estimate each statistic.

    Args:
        scenario: The scenario, whose end is the horizon of every replication.
        planner: The planner of every replication.
        replications: How many replications, at least 2.
        cell_s: The width of the cells of the transient.
        welch_window: The half-width of Welch's moving average, in cells.
        level: The confidence level.
        lead_time_s: The lead time of the planning, if the scenario does not give it.

    Raises:
        InputError: If there are fewer than 2 replications or the cell is not positive.
    """
    if replications < 2:
        raise InputError(f"servono almeno 2 repliche, invece sono {replications}")
    if cell_s <= 0:
        raise InputError(f"la cella del transitorio deve essere > 0, invece è {cell_s}")
    end_s = scenario.settings.end_s
    rng = MultiStreamRng(scenario.settings.seed)
    runs = [
        observe(scenario, planner, rng, lead_time_s).observations
        for _ in range(replications)
    ]
    cells = _cells(end_s, cell_s)
    per_replication = {
        s: tuple(run.mean(s, 0.0, end_s) for run in runs) for s in Statistic
    }
    return ReplicationReport(
        replications=replications,
        seed=scenario.settings.seed,
        level=level,
        per_replication=MappingProxyType(per_replication),
        estimates=MappingProxyType(
            {
                s: confidence_interval(_present(v), level)
                for s, v in per_replication.items()
            }
        ),
        transient=MappingProxyType(
            {s: _transient(runs, s, cells, welch_window, level) for s in Statistic}
        ),
    )


def _cells(end_s: float, cell_s: float) -> list[tuple[float, float]]:
    cells = []
    start = 0.0
    while start < end_s:
        cells.append((start, min(start + cell_s, end_s)))
        start += cell_s
    return cells


def _transient(
    runs: list[RunObservations],
    statistic: Statistic,
    cells: list[tuple[float, float]],
    window: int,
    level: float,
) -> tuple[TransientCell, ...]:
    intervals = [
        confidence_interval(_present(run.mean(statistic, a, b) for run in runs), level)
        for a, b in cells
    ]
    means = [i.mean if i is not None else None for i in intervals]
    welch: list[float | None] = [None] * len(cells)
    complete = [m for m in means if m is not None]
    if len(complete) == len(means) and 1 <= window <= (len(means) - 1) // 2:
        welch[: len(means) - window] = list(welch_moving_average(complete, window))
    return tuple(
        TransientCell(a, b, interval, w)
        for (a, b), interval, w in zip(cells, intervals, welch, strict=True)
    )


def _present(values: Iterable[float | None]) -> list[float]:
    """The values that exist: a replication that observed nothing has no value."""
    return [v for v in values if v is not None]
