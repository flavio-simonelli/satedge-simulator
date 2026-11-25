"""Tests of the periodic kind of contact plan."""

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
