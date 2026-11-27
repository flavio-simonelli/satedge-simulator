"""Tests of the reading of the workload file."""

from pathlib import Path

import pytest

from satedge_simulator.domain.workload import Priority
from satedge_simulator.errors import DocumentError
from satedge_simulator.loading.workload import load_workload


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "workload.yaml"
    path.write_text(text, encoding="utf-8")
    return path


WORKLOAD = """\
schema_version: "1.0.0"
kind: explicit
requests:
  - id: R1
    priority: urgent
    origin: P1-S3
    release_s: 0
    raw_size_gb: 8
    tasks:
      - {execution_s: 120, output_size_gb: 0.5}
  - id: R2
    priority: non_urgent
    origin: P2-S5
    release_s: 300
    arrival_s: 250
    deadline_s: 9000
    raw_size_gb: 12
    tasks: [{execution_s: 150, output_size_gb: 0.001}]
"""


def test_workload_defaults_deadline_from_the_class(tmp_path: Path) -> None:
    requests = load_workload(write(tmp_path, WORKLOAD))
    urgent, non_urgent = requests
    assert urgent.deadline_s == 7200.0
    assert urgent.arrival_s == 0.0
    assert non_urgent.priority is Priority.NON_URGENT
    assert non_urgent.deadline_s == 9000.0
    assert non_urgent.arrival_s == 250.0


def test_workload_rejects_duplicate_identifiers(tmp_path: Path) -> None:
    doc = WORKLOAD.replace("id: R2", "id: R1")
    path = write(tmp_path, doc)
    with pytest.raises(DocumentError, match="duplicate"):
        load_workload(path)


def test_workload_rejects_unknown_priority(tmp_path: Path) -> None:
    path = write(tmp_path, WORKLOAD.replace("urgent", "soon", 1))
    with pytest.raises(DocumentError):
        load_workload(path)
