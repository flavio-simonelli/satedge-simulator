"""The results of the output analysis: a JSON file with the estimates, a CSV file to plot.

Every study writes ``<study>.json`` with its estimates, and a CSV file with one row per point
of what is plotted: the cells of the transient, the batch means, the lags of the
autocorrelation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from satedge_simulator.analysis.autocorrelation_study import AutocorrelationReport
from satedge_simulator.analysis.batch_means import BatchMeansReport
from satedge_simulator.analysis.replications import ReplicationReport
from satedge_simulator.analysis.statistics import ConfidenceInterval

SCHEMA_VERSION = "1.0.0"


def write_replications(directory: str | Path, report: ReplicationReport) -> None:
    """Write ``replications.json`` and ``transient.csv`` in ``directory``."""
    folder = _folder(directory)
    _write_json(
        folder / "replications.json",
        {
            "schema_version": SCHEMA_VERSION,
            "replications": report.replications,
            "seed": report.seed,
            "level": report.level,
            "estimates": {s.value: _interval(i) for s, i in report.estimates.items()},
            "per_replication": {
                s.value: list(v) for s, v in report.per_replication.items()
            },
        },
    )
    rows = [
        [s.value, c.start_s, c.end_s, *_columns(c.interval), c.welch]
        for s, cells in report.transient.items()
        for c in cells
    ]
    _write_csv(
        folder / "transient.csv",
        ["statistic", "start_s", "end_s", "mean", "half_width", "count", "welch"],
        rows,
    )


def write_batch_means(directory: str | Path, report: BatchMeansReport) -> None:
    """Write ``batch_means.json`` and ``batches.csv`` in ``directory``."""
    folder = _folder(directory)
    _write_json(
        folder / "batch_means.json",
        {
            "schema_version": SCHEMA_VERSION,
            "warmup_s": report.warmup_s,
            "end_s": report.end_s,
            "batch_size": report.batch_size,
            "batch_duration_s": report.batch_duration_s,
            "level": report.level,
            "estimates": {
                s.value: {
                    "interval": _interval(b.interval),
                    "batches": len(b.means),
                    "lag1": b.lag1,
                }
                for s, b in report.results.items()
            },
        },
    )
    rows = [
        [s.value, k, mean]
        for s, b in report.results.items()
        for k, mean in enumerate(b.means)
    ]
    _write_csv(folder / "batches.csv", ["statistic", "batch", "mean"], rows)


def write_autocorrelation(directory: str | Path, report: AutocorrelationReport) -> None:
    """Write ``autocorrelation.json`` and ``autocorrelation.csv`` in ``directory``."""
    folder = _folder(directory)
    _write_json(
        folder / "autocorrelation.json",
        {
            "schema_version": SCHEMA_VERSION,
            "warmup_s": report.warmup_s,
            "max_lag": report.max_lag,
            "observations": {s.value: n for s, n in report.observations.items()},
            "autocorrelation": {
                s.value: list(r) for s, r in report.autocorrelation.items()
            },
        },
    )
    rows = [
        [s.value, lag, r]
        for s, values in report.autocorrelation.items()
        for lag, r in enumerate(values, start=1)
    ]
    _write_csv(folder / "autocorrelation.csv", ["statistic", "lag", "r"], rows)


def _interval(i: ConfidenceInterval | None) -> dict[str, Any] | None:
    if i is None:
        return None
    return {
        "mean": i.mean,
        "half_width": i.half_width,
        "count": i.count,
        "level": i.level,
    }


def _columns(i: ConfidenceInterval | None) -> list[Any]:
    return [None, None, 0] if i is None else [i.mean, i.half_width, i.count]


def _folder(directory: str | Path) -> Path:
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(["" if v is None else v for v in row] for row in rows)
