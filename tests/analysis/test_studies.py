"""Tests of the three studies on the stochastic case study, planned by the heuristic."""

from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest
from satedge_workflow_scheduler.solvers.sequential.config import SequentialConfig

from satedge_simulator.analysis.autocorrelation_study import autocorrelation_study
from satedge_simulator.analysis.batch_means import batch_means
from satedge_simulator.analysis.observations import PER_REQUEST, Statistic
from satedge_simulator.analysis.replications import ReplicationReport, replicate
from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.errors import InputError
from satedge_simulator.io.scenario import load_scenario
from satedge_simulator.planning.adapters.scheduler.planner import SchedulerPlanner

EXAMPLE = (
    Path(__file__).parents[2] / "examples" / "casostudio" / "scenario-stocastico.yaml"
)


@cache
def scenario() -> Scenario:
    return load_scenario(EXAMPLE).scenario


def planner() -> SchedulerPlanner:
    return SchedulerPlanner(SequentialConfig(), horizon_s=scenario().world_horizon_s)


@cache
def three_replications() -> ReplicationReport:
    return replicate(
        scenario(), planner(), replications=3, cell_s=7200.0, welch_window=1
    )


def test_each_replication_gives_one_value_per_statistic() -> None:
    report = three_replications()
    assert report.replications == 3
    for statistic in Statistic:
        assert len(report.per_replication[statistic]) == 3
        estimate = report.estimates[statistic]
        assert estimate is not None
        assert estimate.count == 3
    responses = report.per_replication[Statistic.RESPONSE]
    assert len(set(responses)) == 3  # independent replications: three different values


def test_the_transient_has_one_cell_per_step_of_the_grid() -> None:
    cells = three_replications().transient[Statistic.HPC_UTILIZATION]
    assert [(c.start_s, c.end_s) for c in cells] == [
        (0.0, 7200.0),
        (7200.0, 14400.0),
        (14400.0, 21600.0),
        (21600.0, 28800.0),
    ]
    assert all(c.interval is not None for c in cells)
    assert cells[0].welch == cells[0].interval.mean  # type: ignore[union-attr]
    assert cells[-1].welch is None  # the last window cells have no moving average


def test_the_first_replication_is_the_run_planted_from_the_seed() -> None:
    one_more = replicate(
        scenario(), planner(), replications=2, cell_s=7200.0, welch_window=1
    )
    first = three_replications().per_replication[Statistic.RESPONSE][0]
    assert one_more.per_replication[Statistic.RESPONSE][0] == first


def test_replications_need_at_least_two() -> None:
    the_scenario, the_planner = scenario(), planner()
    with pytest.raises(InputError, match="almeno 2"):
        replicate(
            the_scenario, the_planner, replications=1, cell_s=3600.0, welch_window=1
        )


def test_batch_means_discard_the_warmup_and_cut_whole_batches() -> None:
    report = batch_means(
        scenario(), planner(), warmup_s=5640.0, batch_size=4, batch_duration_s=5640.0
    )
    assert report.results[Statistic.HPC_UTILIZATION].means
    assert (
        len(report.results[Statistic.HPC_UTILIZATION].means) == (28800 - 5640) // 5640
    )
    response = report.results[Statistic.RESPONSE]
    assert response.interval is not None
    assert response.interval.count == len(response.means)


def test_the_warmup_must_be_before_the_end() -> None:
    the_scenario, the_planner = scenario(), planner()
    with pytest.raises(InputError, match="riscaldamento"):
        batch_means(
            the_scenario,
            the_planner,
            warmup_s=28800.0,
            batch_size=4,
            batch_duration_s=5640.0,
        )


def test_the_autocorrelation_covers_the_per_request_statistics() -> None:
    report = autocorrelation_study(scenario(), planner(), warmup_s=0.0, max_lag=3)
    assert set(report.autocorrelation) == PER_REQUEST
    for statistic, values in report.autocorrelation.items():
        assert len(values) == 3 or report.observations[statistic] <= 3


def test_a_shorter_scenario_has_fewer_observations() -> None:
    short = replace(scenario(), settings=replace(scenario().settings, end_s=7200.0))
    report = autocorrelation_study(short, planner(), warmup_s=0.0, max_lag=1)
    longer = autocorrelation_study(scenario(), planner(), warmup_s=0.0, max_lag=1)
    assert (
        report.observations[Statistic.RESPONSE]
        < longer.observations[Statistic.RESPONSE]
    )
