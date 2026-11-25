"""Tests of the reading of the topology file."""

from pathlib import Path

import pytest
import yaml

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import DocumentError
from satedge_simulator.io.contact_plan import ContactPlan
from satedge_simulator.io.topology import load_topology

VALID = """\
schema_version: "1.0.0"
kind: ring_constellation
planes: 2
satellites_per_plane: 3
horizon_s: 1000
plmm_capacity_gb: 2000
hpc: {period_s: 100, duration_s: 30, startup_s: 10}
"""


def contact_plan() -> ContactPlan:
    return ContactPlan(
        {
            ("COM1", "COM2"): WindowSet([Window(100.0, 200.0)]),
            ("COM1", "GS"): WindowSet([Window(300.0, 400.0)]),
            ("COM2", "GS"): WindowSet([Window(500.0, 600.0)]),
        }
    )


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "topology.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_the_ring_with_its_windows(tmp_path: Path) -> None:
    constellation = load_topology(write(tmp_path, VALID), contact_plan())
    assert len(constellation.satellites) == 6
    link = constellation.link_between("COM1", "GS")
    assert link is not None
    assert link.is_windowed


def test_hpc_windows_use_the_usable_length(tmp_path: Path) -> None:
    constellation = load_topology(write(tmp_path, VALID), contact_plan())
    first = constellation.satellite("COM1").hpc_windows.windows[0]
    assert first.duration == 20.0  # 30 s of window, 10 s of container start-up


def test_unknown_field_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="topology.yaml"):
        load_topology(write(tmp_path, VALID + "speed: 3\n"), contact_plan())


def test_unsupported_version_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DocumentError):
        load_topology(
            write(tmp_path, VALID.replace('"1.0.0"', '"3.0.0"')), contact_plan()
        )


def test_missing_contact_windows_are_a_document_error(tmp_path: Path) -> None:
    with pytest.raises(DocumentError):
        load_topology(write(tmp_path, VALID), ContactPlan({}))


def test_unsupported_kind_is_an_explicit_error(tmp_path: Path) -> None:
    text = VALID.replace("kind: ring_constellation", "kind: explicit")
    with pytest.raises(
        DocumentError, match="tipo di topologia non supportato 'explicit'"
    ) as info:
        load_topology(write(tmp_path, text), contact_plan())
    assert "ring_constellation" in str(info.value)


def test_missing_kind_is_an_error(tmp_path: Path) -> None:
    text = VALID.replace("kind: ring_constellation\n", "")
    with pytest.raises(DocumentError, match="kind"):
        load_topology(write(tmp_path, text), contact_plan())


def test_every_field_reaches_the_ring_spec(tmp_path: Path) -> None:
    """Round trip: every field of the file must arrive at the ring spec, with its value."""
    from satedge_simulator.io.ring import HpcSchedule, LinkParams, RingSpec
    from satedge_simulator.io.topology import TopologyDoc

    text = """\
schema_version: "1.0.0"
kind: ring_constellation
ground_station: TERRA
planes: 3
satellites_per_plane: 4
com_index: 1
horizon_s: 500
plmm_capacity_gb: 300
plmm_overrides_gb: {P1-S0: 50}
hpc_rate_gbps: 2
hpc: {period_s: 200, duration_s: 60, startup_s: 5}
hpc_phases_s: {P2-S2: 7}
intra_link: {capacity_gbps: 3, latency_s: 0.1}
inter_link: {capacity_gbps: 4, latency_s: 0.2}
ground_link: {capacity_gbps: 5, latency_s: 0.3}
"""
    spec = TopologyDoc.model_validate(yaml.safe_load(text)).to_spec(500.0)
    assert spec == RingSpec(
        planes=3,
        satellites_per_plane=4,
        com_index=1,
        horizon_s=500.0,
        plmm_capacity_gb=300.0,
        hpc_rate_gbps=2.0,
        plmm_overrides_gb={"P1-S0": 50.0},
        hpc=HpcSchedule(period_s=200.0, duration_s=60.0, startup_s=5.0),
        hpc_phases_s={"P2-S2": 7.0},
        intra_link=LinkParams(capacity_gbps=3.0, latency_s=0.1),
        inter_link=LinkParams(capacity_gbps=4.0, latency_s=0.2),
        ground_link=LinkParams(capacity_gbps=5.0, latency_s=0.3),
        ground_station_id="TERRA",
    )


def test_without_a_horizon_the_windows_go_to_the_end_of_the_simulation(
    tmp_path: Path,
) -> None:
    text = "\n".join(
        line for line in VALID.splitlines() if not line.startswith("horizon_s")
    )
    constellation = load_topology(
        write(tmp_path, text + "\n"), contact_plan(), horizon_s=50_000.0
    )
    last = constellation.satellites[0].hpc_windows.windows[-1]
    assert (
        50_000.0 - 100.0 <= last.start < 50_000.0
    )  # the windows of VALID repeat every 100 s


def test_a_horizon_shorter_than_the_simulation_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="finestre di calcolo fino a"):
        load_topology(write(tmp_path, VALID), contact_plan(), horizon_s=1e9)
