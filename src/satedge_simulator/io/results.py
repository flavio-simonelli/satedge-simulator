"""The results of a simulation, written as ``metrics.json``."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from satedge_simulator.domain.lifecycle import RequestRecord
from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.metrics.plmm import PlmmUsage
from satedge_simulator.metrics.requests import ClassMetrics
from satedge_simulator.metrics.resources import ResourceUsage
from satedge_simulator.metrics.summary import SimulationMetrics
from satedge_simulator.planning.adapters.scheduler.verification import AsRunFinding

SCHEMA_VERSION = "1.0.0"


def results_document(
    end_s: float,
    metrics: SimulationMetrics,
    records: Mapping[str, RequestRecord],
    findings: Iterable[AsRunFinding],
) -> dict[str, Any]:
    """The results as plain JSON values: the metrics, the check of the as-run, each request."""
    found = list(findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "end_s": end_s,
        "requests": [_class(c) for c in metrics.requests],
        "hpcs": {node: _usage(u) for node, u in metrics.hpcs.items()},
        "arcs": {f"{s}->{t}": _usage(u) for (s, t), u in metrics.arcs.items()},
        "plmms": {node: _plmm(u) for node, u in metrics.plmms.items()},
        "epochs": {
            "epochs": metrics.epochs.epochs,
            "new": metrics.epochs.new,
            "accepted": metrics.epochs.accepted,
            "rejected": metrics.epochs.rejected,
            "solver_time_s": _distribution(metrics.epochs.solver_time),
            "overruns": metrics.epochs.overruns,
            "max_unreachable": metrics.epochs.max_unreachable,
        },
        "violations": {kind.value: n for kind, n in metrics.violations.items()},
        "deviation_s": _distribution(metrics.deviation),
        "lost_raw": metrics.lost_raw,
        "verification": {
            "passed": not found,
            "findings": [
                {
                    "epoch": f.epoch,
                    "constraint": f.constraint,
                    "request_id": f.request_id,
                    "message": f.message,
                }
                for f in found
            ],
        },
        "outcomes": {
            request_id: {
                "status": record.status.value,
                "history": [[at, status.value] for at, status in record.history],
            }
            for request_id, record in records.items()
        },
    }


def write_metrics(
    path: str | Path,
    end_s: float,
    metrics: SimulationMetrics,
    records: Mapping[str, RequestRecord],
    findings: Iterable[AsRunFinding],
) -> None:
    """Write the results of a simulation to ``path``, creating its directory if needed."""
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    document = results_document(end_s, metrics, records, findings)
    file.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _class(c: ClassMetrics) -> dict[str, Any]:
    return {
        "priority": c.priority.value,
        "arrived": c.arrived,
        "accepted": c.accepted,
        "rejected": c.rejected,
        "delivered_on_time": c.delivered_on_time,
        "delivered_late": c.delivered_late,
        "failed": c.failed,
        "unfinished": c.unfinished,
        "response_from_release_s": _distribution(c.response_from_release),
        "response_from_arrival_s": _distribution(c.response_from_arrival),
        "tardiness_s": _distribution(c.tardiness),
    }


def _usage(u: ResourceUsage) -> dict[str, Any]:
    return {
        "busy_s": u.busy_s,
        "available_s": u.available_s,
        "utilization": u.utilization,
    }


def _plmm(u: PlmmUsage) -> dict[str, Any]:
    return {
        "capacity_gb": u.capacity_gb,
        "peak_gb": u.peak_gb,
        "mean_gb": u.mean_gb,
        "peak_ratio": u.peak_ratio,
    }


def _distribution(d: Distribution) -> dict[str, Any]:
    return {"count": d.count, "mean": d.mean, "p50": d.p50, "p95": d.p95, "max": d.max}
