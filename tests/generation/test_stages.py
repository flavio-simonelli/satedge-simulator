"""Tests of the split of a pipeline into stages that fit in a computing window."""

import pytest

from satedge_simulator.errors import StateError
from satedge_simulator.generation.stages import StageSplitter

# a window of 300 s, an HPC at 1 Gbps, intermediate outputs up to 1.2 times their input
SPLITTER = StageSplitter(
    (1, 3), window_s=300.0, rate_gbps=1.0, worst_ratio=1.2, worst_final_gb=0.001
)


def test_a_small_pipeline_keeps_the_drawn_stages() -> None:
    assert SPLITTER.fewest(raw_gb=2.0, work_s_per_gb=12.0) == 1
    assert SPLITTER.stages(drawn=3, raw_gb=2.0, work_s_per_gb=12.0) == 3


def test_a_large_pipeline_is_split_until_every_task_fits() -> None:
    # in one stage: 12 + 0.001 s of I/O and 288 s of work, which is not strictly below 300 s
    assert SPLITTER.fewest(raw_gb=12.0, work_s_per_gb=24.0) == 2
    assert SPLITTER.stages(drawn=1, raw_gb=12.0, work_s_per_gb=24.0) == 2


def test_a_task_that_exactly_fills_the_window_does_not_fit() -> None:
    exact = StageSplitter(
        (1, 1), window_s=300.0, rate_gbps=1.0, worst_ratio=1.0, worst_final_gb=0.0
    )
    assert exact.fewest(raw_gb=10.0, work_s_per_gb=29.0) is None  # 10 s + 290 s = 300 s


def test_no_split_that_fits_is_a_defect() -> None:
    tight = StageSplitter(
        (1, 1), window_s=10.0, rate_gbps=1.0, worst_ratio=1.0, worst_final_gb=0.0
    )
    with pytest.raises(StateError, match="nessuna scomposizione"):
        tight.stages(drawn=1, raw_gb=12.0, work_s_per_gb=24.0)
