"""Tests of the periodic and Orekit kinds of contact plan."""

import json
from pathlib import Path

import pytest

from satedge_simulator.domain.intervals import Window
from satedge_simulator.errors import DocumentError
from satedge_simulator.io.contact_plan import load_contact_plan

EXAMPLE = Path(__file__).parents[2] / "examples" / "casostudio"
PAIRS = (("COM1", "COM2"), ("COM1", "GS"), ("COM2", "GS"))


def test_the_periodic_plan_of_the_case_study_is_its_explicit_plan() -> None:
    periodic = load_contact_plan(
        EXAMPLE / "contact_plan_periodico.yaml", horizon_s=28800.0
    )
    explicit = load_contact_plan(EXAMPLE / "contact_plan.yaml")
    for a, b in PAIRS:
        assert periodic.windows_of(a, b) == explicit.windows_of(a, b)


def test_a_periodic_plan_covers_any_horizon() -> None:
    plan = load_contact_plan(
        EXAMPLE / "contact_plan_periodico.yaml", horizon_s=10 * 86400.0
    )
    windows = plan.windows_of("COM1", "GS").windows
    # one every 2820 s from 2400 s, while it opens before ten days
    assert len(windows) == (10 * 86400 - 2400) // 2820 + 1
    assert windows[-1].start < 10 * 86400.0
    assert windows[1] == Window(5220.0, 5400.0)


def test_a_periodic_plan_needs_the_horizon() -> None:
    with pytest.raises(DocumentError, match="orizzonte"):
        load_contact_plan(EXAMPLE / "contact_plan_periodico.yaml")


def test_periodic_windows_must_not_overlap(tmp_path: Path) -> None:
    path = tmp_path / "plan.yaml"
    path.write_text(
        'schema_version: "1.0.0"\nkind: periodic\nlinks:\n'
        "  - {a: COM1, b: GS, first_start_s: 0, period_s: 100, duration_s: 100}\n",
        encoding="utf-8",
    )
    with pytest.raises(DocumentError, match="durata < periodo"):
        load_contact_plan(path, horizon_s=1000.0)


def orekit_result() -> dict[str, object]:
    """A result of isl-windows-visibility, with the fields the simulator does not read."""
    window = {
        "start": "2026-03-01T00:16:27.450528Z",
        "end": "2026-03-01T00:30:30.290080Z",
        "start_offset_s": 987.450528,
        "end_offset_s": 1830.29008,
        "min_range_km": 1231.1,
        "max_range_km": 4524.8,
        "mean_range_km": 2636.1,
    }
    return {
        "schema_version": "1.1.0",
        "generator": {"name": "isl-windows-visibility", "version": "0.1.0"},
        "generated_at": "2026-10-22T15:39:44Z",
        "config_sha256": "0" * 64,
        "time_scale": "UTC",
        "horizon": {"start": "2026-03-01T00:00:00Z", "end": "2026-03-02T00:00:00Z"},
        "links": [
            {"node_a": "COM1", "node_b": "COM2", "windows": [window]},
            {"node_a": "COM1", "node_b": "GS1", "windows": [window]},
        ],
    }


def test_an_orekit_plan_reads_the_offsets_and_renames_the_nodes(tmp_path: Path) -> None:
    (tmp_path / "result.json").write_text(json.dumps(orekit_result()), encoding="utf-8")
    path = tmp_path / "plan.yaml"
    path.write_text(
        'schema_version: "1.0.0"\nkind: orekit\nsource: result.json\nnames: {GS1: GS}\n',
        encoding="utf-8",
    )
    plan = load_contact_plan(path)
    assert plan.windows_of("COM2", "COM1").windows == (Window(987.450528, 1830.29008),)
    assert plan.windows_of("GS", "COM1").windows == (Window(987.450528, 1830.29008),)


def test_a_missing_orekit_result_names_its_file(tmp_path: Path) -> None:
    path = tmp_path / "plan.yaml"
    path.write_text(
        'schema_version: "1.0.0"\nkind: orekit\nsource: absent.json\n', encoding="utf-8"
    )
    with pytest.raises(DocumentError, match="absent.json"):
        load_contact_plan(path)
