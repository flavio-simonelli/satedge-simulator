"""Tests of the generator of the stochastic workload, on the constellation of the case study."""

import statistics
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from satedge_simulator.domain.topology import Constellation
from satedge_simulator.domain.workload import Priority, RequestSpec
from satedge_simulator.domain.workload_model import Range, WorkloadModel
from satedge_simulator.errors import ScenarioError
from satedge_simulator.generation.generator import RequestGenerator
from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.rng.rngs import MultiStreamRng

EXAMPLE = Path(__file__).parents[2] / "examples" / "casostudio" / "scenario.yaml"
MODEL = WorkloadModel(arrivals_per_hour=4.0)


@cache
def constellation() -> Constellation:
    return load_scenario(EXAMPLE).scenario.constellation


def draw(
    model: WorkloadModel = MODEL, seed: int = 123_456_789, n: int = 2000
) -> list[RequestSpec]:
    generator = RequestGenerator(model, constellation(), MultiStreamRng(seed))
    t = 0.0
    requests = []
    for _ in range(n):
        t += generator.next_interarrival_s()
        requests.append(generator.request(t))
    return requests


def occupancy(request: RequestSpec, rate_gbps: float) -> list[float]:
    sizes = request.data_sizes_gb()
    return [
        (sizes[k] + sizes[k + 1]) / rate_gbps + task.execution_s
        for k, task in enumerate(request.tasks)
    ]


def test_the_same_seed_draws_the_same_workload() -> None:
    assert draw(n=50) == draw(n=50)
    assert draw(n=50) != draw(seed=42, n=50)


def test_every_task_fits_strictly_in_a_computing_window() -> None:
    generator = RequestGenerator(MODEL, constellation(), MultiStreamRng(1))
    assert generator.window_s == 300.0
    rate = min(s.hpc_rate_gbps for s in constellation().satellites)
    worst = max(o for r in draw() for o in occupancy(r, rate))
    assert worst < 300.0


def test_a_pipeline_is_split_more_finely_when_a_task_would_not_fit() -> None:
    # 12 Gb at 24 s/Gb is 288 s of work: in one stage, with the I/O, it does not fit
    heavy = replace(
        MODEL, raw_size_gb=Range(12.0, 12.0), work_s_per_gb=Range(24.0, 24.0)
    )
    assert min(len(r.tasks) for r in draw(heavy, n=200)) == 2


def test_parameters_that_cannot_fit_in_a_window_are_rejected() -> None:
    heavy = replace(
        MODEL,
        stages=(1, 1),
        raw_size_gb=Range(12.0, 12.0),
        work_s_per_gb=Range(24.0, 24.0),
    )
    with pytest.raises(ScenarioError, match="finestra di calcolo"):
        RequestGenerator(heavy, constellation(), MultiStreamRng(1))


def test_the_quantities_stay_in_their_ranges() -> None:
    coms = {p.com for p in constellation().planes}
    for r in draw():
        assert 0.0 <= r.release_s - r.arrival_s <= 5640.0
        assert 2.0 <= r.raw_size_gb <= 12.0
        assert 1 <= len(r.tasks) <= 3
        assert 0.0001 <= r.output_size_gb <= 0.001
        assert r.origin not in coms
        delay = {Priority.URGENT: 7200.0, Priority.NON_URGENT: 25200.0}[r.priority]
        assert r.deadline_s == pytest.approx(r.release_s + delay)
        work = sum(t.execution_s for t in r.tasks) / r.raw_size_gb
        assert 12.0 <= work <= 24.0
        sizes = r.data_sizes_gb()
        for k in range(len(r.tasks) - 1):
            assert 0.8 <= sizes[k + 1] / sizes[k] <= 1.2


def test_the_arrivals_are_poisson_and_the_classes_bernoulli() -> None:
    requests = draw(n=20_000)
    arrivals = [r.arrival_s for r in requests]
    gaps = [b - a for a, b in zip([0.0, *arrivals], arrivals, strict=False)]
    assert statistics.fmean(gaps) == pytest.approx(900.0, rel=0.03)
    assert statistics.stdev(gaps) == pytest.approx(
        900.0, rel=0.03
    )  # exponential: cv = 1
    urgent = sum(r.priority is Priority.URGENT for r in requests) / len(requests)
    assert urgent == pytest.approx(0.5, abs=0.02)


def test_each_quantity_has_its_own_stream() -> None:
    # changing the class probability changes the classes, not the raw data or the arrivals
    base = draw(n=100)
    other = draw(replace(MODEL, urgent_probability=0.9), n=100)
    assert [r.raw_size_gb for r in base] == [r.raw_size_gb for r in other]
    assert [r.arrival_s for r in base] == [r.arrival_s for r in other]
    assert [r.priority for r in base] != [r.priority for r in other]


def test_an_unknown_origin_is_rejected() -> None:
    with pytest.raises(ScenarioError, match="GHOST"):
        RequestGenerator(
            replace(MODEL, origins=("GHOST",)), constellation(), MultiStreamRng(1)
        )
