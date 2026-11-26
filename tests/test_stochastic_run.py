"""Tests of runs with the stochastic workload, on the case study planned by the heuristic."""

from dataclasses import replace
from pathlib import Path

from satedge_workflow_scheduler.solvers.sequential.config import SequentialConfig

from satedge_simulator.api import simulate_file
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.planning.adapters.scheduler.planner import SchedulerPlanner
from satedge_simulator.rng.rngs import MultiStreamRng
from satedge_simulator.runtime.simulation import Simulation, SimulationOutcome

EXAMPLE = (
    Path(__file__).parent.parent
    / "examples"
    / "casostudio"
    / "scenario-stocastico.yaml"
)


def scenario(seed: int = 123_456_789) -> Scenario:
    loaded = load_scenario(EXAMPLE).scenario
    return replace(loaded, settings=replace(loaded.settings, seed=seed))


def run(s: Scenario, rng: MultiStreamRng | None = None) -> SimulationOutcome:
    planner = SchedulerPlanner(SequentialConfig(), horizon_s=s.settings.end_s)
    return Simulation(s, planner, rng=rng).run()


def history(outcome: SimulationOutcome) -> dict[str, list[tuple[float, str]]]:
    return {i: [(t, s.value) for t, s in r.history] for i, r in outcome.records.items()}


def test_the_requests_are_drawn_during_the_run() -> None:
    outcome = run(scenario())
    assert outcome.requests
    assert all(r.id.startswith("G") for r in outcome.requests)
    assert all(0.0 < r.arrival_s < 28800.0 for r in outcome.requests)
    assert set(outcome.records) == {r.id for r in outcome.requests}


def test_the_same_seed_gives_the_same_run_and_another_seed_another() -> None:
    first, second = history(run(scenario())), history(run(scenario()))
    assert first == second
    assert history(run(scenario())) != history(run(scenario(seed=42)))


def test_replications_on_one_generator_go_on_where_the_previous_stopped() -> None:
    rng = MultiStreamRng(123_456_789)
    first = run(scenario(), rng)
    drawn_after_first = rng.stream(0).drawn
    second = run(scenario(), rng)
    assert rng.stream(0).drawn > drawn_after_first
    assert [r.arrival_s for r in first.requests] != [
        r.arrival_s for r in second.requests
    ]
    # the first replication is the run planted from the seed
    assert history(first) == history(run(scenario()))


def test_the_stochastic_example_passes_the_check_against_the_model() -> None:
    result = simulate_file(EXAMPLE)
    assert result.verified
    assert result.outcome.violations == ()


def test_the_world_reaches_beyond_the_end_of_the_run() -> None:
    # the observation stops at 8 h, but a request generated near the end is planned against
    # the windows after it: they reach the end plus the longest life of a request
    loaded = load_scenario(EXAMPLE).scenario
    model = loaded.workload_model
    assert model is not None
    assert loaded.world_horizon_s == 28800.0 + model.longest_life_s
    last_window = max(
        w.end for s in loaded.constellation.satellites for w in s.hpc_windows
    )
    assert last_window > 28800.0 + 25200.0


def test_requests_near_the_end_are_not_rejected_for_lack_of_windows() -> None:
    outcome = run(scenario())
    rejected = [rid for _, d in outcome.decisions for rid in d.rejected]
    assert rejected == []
