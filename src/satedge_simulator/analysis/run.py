"""One observed run: the simulation with the collector of the time series on its bus."""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.analysis.observations import RunObservations, TimeSeriesCollector
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.planning.ports import Planner
from satedge_simulator.rng.rngs import MultiStreamRng
from satedge_simulator.runtime.simulation import Simulation, SimulationOutcome


@dataclass(frozen=True, slots=True)
class ObservedRun:
    """What one run produced, and its observations for the output analysis."""

    outcome: SimulationOutcome
    observations: RunObservations


def observe(
    scenario: Scenario,
    planner: Planner,
    rng: MultiStreamRng,
    lead_time_s: float | None = None,
) -> ObservedRun:
    """Run ``scenario`` once, drawing from ``rng``, and collect its observations.

    The generator goes on where the previous run left it, so consecutive runs on the same
    ``rng`` never reuse a number.
    """
    bus = EventBus()
    collector = TimeSeriesCollector()
    collector.attach(bus)
    outcome = Simulation(scenario, planner, lead_time_s, bus, rng).run()
    observations = RunObservations.of_run(
        outcome.records,
        outcome.requests,
        collector,
        scenario.constellation,
        outcome.end_s,
    )
    return ObservedRun(outcome, observations)
