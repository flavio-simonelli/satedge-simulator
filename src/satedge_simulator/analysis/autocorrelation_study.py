"""The autocorrelation of the per-request statistics of one long run, to choose the batch size.

The observations of the requests that follow one another are correlated: they share the same
epochs, the same windows, the same queue. The autocorrelation at lag ``j`` measures how much;
a batch size well beyond the lag where it fades makes the batch means about independent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from satedge_simulator.analysis.autocorrelation import autocorrelation
from satedge_simulator.analysis.observations import PER_REQUEST, Statistic
from satedge_simulator.analysis.run import observe
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.errors import InputError
from satedge_simulator.planning.ports import Planner
from satedge_simulator.rng.rngs import MultiStreamRng


@dataclass(frozen=True, slots=True)
class AutocorrelationReport:
    """The autocorrelation of each per-request statistic after the warm-up.

    Attributes:
        warmup_s: The part of the run discarded.
        max_lag: The largest lag.
        observations: How many observations each statistic has after the warm-up.
        autocorrelation: ``r_1, …, r_max_lag`` of each statistic; empty when it has too few
            observations for the largest lag.
    """

    warmup_s: float
    max_lag: int
    observations: Mapping[Statistic, int]
    autocorrelation: Mapping[Statistic, tuple[float, ...]]


def autocorrelation_study(
    scenario: Scenario,
    planner: Planner,
    warmup_s: float,
    max_lag: int,
    lead_time_s: float | None = None,
) -> AutocorrelationReport:
    """Run ``scenario`` once and measure the autocorrelation of its per-request statistics.

    Raises:
        InputError: If the largest lag is not positive.
    """
    if max_lag < 1:
        raise InputError(f"il lag massimo deve essere almeno 1, invece è {max_lag}")
    run = observe(
        scenario, planner, MultiStreamRng(scenario.settings.seed), lead_time_s
    )
    series = {
        s: [o.value for o in run.observations.observations(s) if o.time_s >= warmup_s]
        for s in sorted(PER_REQUEST)
    }
    return AutocorrelationReport(
        warmup_s=warmup_s,
        max_lag=max_lag,
        observations=MappingProxyType({s: len(v) for s, v in series.items()}),
        autocorrelation=MappingProxyType(
            {
                s: autocorrelation(v, max_lag) if len(v) > max_lag else ()
                for s, v in series.items()
            }
        ),
    )
