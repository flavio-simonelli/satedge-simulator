"""Tests of the ring constellation builder, on the parameters of the case study."""

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import ScenarioError
from satedge_simulator.io.contact_plan import ContactPlan
from satedge_simulator.io.ring import (
    HpcSchedule,
    RingConstellationBuilder,
    RingSpec,
    node_name,
    periodic_windows,
    ring_pairs,
)

CASE_STUDY = RingSpec(
    planes=2,
    satellites_per_plane=9,
    com_index=0,
    horizon_s=28800.0,
    plmm_capacity_gb=2000.0,
    hpc=HpcSchedule(period_s=5640.0, duration_s=300.0, startup_s=0.0),
)


def contact_plan() -> ContactPlan:
    return ContactPlan(
        {
            ("COM1", "COM2"): WindowSet([Window(600.0, 1200.0)]),
            ("COM1", "GS"): WindowSet([Window(100.0, 280.0)]),
            ("COM2", "GS"): WindowSet([Window(900.0, 1080.0)]),
        }
    )


def test_node_names_follow_the_convention() -> None:
    assert node_name(1, 0, com_index=0) == "COM1"
    assert node_name(2, 3, com_index=0) == "P2-S3"


@pytest.mark.parametrize(
    ("size", "expected"),
    [(1, []), (2, [(0, 1)]), (3, [(0, 1), (1, 2), (2, 0)])],
)
def test_ring_pairs(size: int, expected: list[tuple[int, int]]) -> None:
    assert ring_pairs(size) == expected


def test_periodic_windows_repeat_until_the_horizon() -> None:
    hpc = HpcSchedule(period_s=100.0, duration_s=30.0, startup_s=10.0)
    windows = periodic_windows(phase_s=5.0, hpc=hpc, horizon_s=250.0)
    assert [w.start for w in windows] == [5.0, 105.0, 205.0]
    assert all(w.duration == 20.0 for w in windows)


def test_case_study_ring_has_18_satellites_and_21_links() -> None:
    constellation = RingConstellationBuilder(CASE_STUDY, contact_plan()).build()
    assert len(constellation.satellites) == 18
    assert len(constellation.planes) == 2
    # 9 intra-plane links per plane (18), 1 COM-COM link, 2 COM-ground links
    assert len(constellation.links) == 21


def test_case_study_has_three_windowed_links() -> None:
    constellation = RingConstellationBuilder(CASE_STUDY, contact_plan()).build()
    windowed = [link for link in constellation.links if link.is_windowed]
    assert {link.name for link in windowed} == {"COM1-COM2", "COM1-GS", "COM2-GS"}


def test_default_phases_spread_the_windows_over_the_period() -> None:
    constellation = RingConstellationBuilder(CASE_STUDY, contact_plan()).build()
    starts = [s.hpc_windows.windows[0].start for s in constellation.satellites]
    assert starts[0] == 0.0
    assert starts[1] == pytest.approx(5640.0 / 18)


def test_com_is_the_satellite_at_com_index() -> None:
    constellation = RingConstellationBuilder(CASE_STUDY, contact_plan()).build()
    assert constellation.planes[0].com == "COM1"
    assert constellation.planes[1].com == "COM2"


def test_unknown_override_is_rejected() -> None:
    spec = RingSpec(
        planes=1,
        satellites_per_plane=3,
        com_index=0,
        horizon_s=100.0,
        plmm_capacity_gb=10.0,
        plmm_overrides_gb={"P9-S9": 5.0},
    )
    with pytest.raises(ScenarioError):
        RingConstellationBuilder(spec, ContactPlan({}))


def test_com_index_out_of_range_is_rejected() -> None:
    with pytest.raises(ScenarioError):
        RingSpec(
            planes=1,
            satellites_per_plane=2,
            com_index=2,
            horizon_s=10.0,
            plmm_capacity_gb=1.0,
        )


def test_missing_contact_windows_are_an_error() -> None:
    builder = RingConstellationBuilder(CASE_STUDY, ContactPlan({}))
    with pytest.raises(ScenarioError):
        builder.build()
