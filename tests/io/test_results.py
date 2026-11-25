"""Tests of the document of the results."""

import json
from pathlib import Path

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.topology import (
    Constellation,
    GroundStation,
    Link,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.io.results import SCHEMA_VERSION, results_document, write_metrics
from satedge_simulator.metrics.as_run import AsRun
from satedge_simulator.metrics.epochs import EpochCollector
from satedge_simulator.metrics.plmm import PlmmCollector
from satedge_simulator.metrics.resources import ResourceCollector
from satedge_simulator.metrics.summary import SimulationMetrics, summarize
from satedge_simulator.planning.adapters.scheduler.verification import AsRunFinding

FINDING = AsRunFinding(0, "(3) precedence", "R1", "task 1 starts before task 0 ends")


def metrics() -> SimulationMetrics:
    net = Constellation(
        [
            Plane(
                1, (Satellite("A", 10.0, 1.0, WindowSet([Window(0.0, 50.0)])),), com="A"
            )
        ],
        GroundStation("GS"),
        [
            Link(
                "A",
                "GS",
                1.0,
                0.01,
                WindowedAvailability(WindowSet([Window(10.0, 20.0)])),
            )
        ],
    )
    return summarize(
        100.0,
        (),
        {},
        [Violation(5.0, ViolationKind.PLMM_FULL, "R1", "A")],
        (),
        AsRun(),
        ResourceCollector(net),
        PlmmCollector(net),
        EpochCollector(),
        lost_raw=0,
    )


def record() -> RequestRecord:
    r = RequestRecord("R1", history=[(1.0, RequestStatus.ARRIVED)])
    r.move(RequestStatus.QUEUED, 1.0)
    r.move(RequestStatus.UNFINISHED, 100.0)
    return r


def test_the_document_holds_plain_json_values() -> None:
    document = results_document(100.0, metrics(), {"R1": record()}, [FINDING])
    assert json.loads(json.dumps(document)) == document
    assert document["schema_version"] == SCHEMA_VERSION
    assert document["arcs"]["A->GS"] == {
        "busy_s": 0.0,
        "available_s": 10.0,
        "utilization": 0.0,
    }
    assert document["violations"] == {"plmm_full": 1}
    assert document["outcomes"]["R1"] == {
        "status": "unfinished",
        "history": [[1.0, "arrived"], [1.0, "queued"], [100.0, "unfinished"]],
    }


def test_the_findings_of_the_check_are_listed() -> None:
    document = results_document(100.0, metrics(), {}, [FINDING])
    assert document["verification"] == {
        "passed": False,
        "findings": [
            {
                "epoch": 0,
                "constraint": "(3) precedence",
                "request_id": "R1",
                "message": "task 1 starts before task 0 ends",
            }
        ],
    }


def test_write_creates_the_directory(tmp_path: Path) -> None:
    path = tmp_path / "out" / "metrics.json"
    write_metrics(path, 100.0, metrics(), {}, [])
    assert json.loads(path.read_text(encoding="utf-8"))["verification"]["passed"]
