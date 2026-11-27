"""The results of a simulation, as the file ``metrics.json`` holds them.

This module describes the document and writes it. It knows nothing of the domain: the document
is built from the objects of the simulation by :mod:`satedge_simulator.export.results`.
"""

from __future__ import annotations

from satedge_simulator.io.base import Document

SCHEMA_VERSION = "1.0.0"


class DistributionDoc(Document):
    """A distribution of values: how many, and its mean, quantiles and maximum."""

    count: int
    mean: float | None = None
    p50: float | None = None
    p95: float | None = None
    max: float | None = None


class ClassDoc(Document):
    """The metrics of one priority class."""

    priority: str
    arrived: int
    accepted: int
    rejected: int
    delivered_on_time: int
    delivered_late: int
    failed: int
    unfinished: int
    response_from_release_s: DistributionDoc
    response_from_arrival_s: DistributionDoc
    tardiness_s: DistributionDoc


class UsageDoc(Document):
    """How much a resource was busy, out of the time it was available."""

    busy_s: float
    available_s: float
    utilization: float | None = None


class PlmmDoc(Document):
    """The memory of a PLMM: its capacity, and how much of it was used."""

    capacity_gb: float
    peak_gb: float
    mean_gb: float
    peak_ratio: float | None = None


class EpochsDoc(Document):
    """The decisions of the planner, summed over the epochs."""

    epochs: int
    new: int
    accepted: int
    rejected: int
    solver_time_s: DistributionDoc
    overruns: int
    max_unreachable: int


class FindingDoc(Document):
    """A constraint of the final model that the as-run calendar does not respect."""

    epoch: int
    constraint: str
    request_id: str | None = None
    message: str


class VerificationDoc(Document):
    """The check of the as-run: whether it passed, and each finding."""

    passed: bool
    findings: list[FindingDoc]


class OutcomeDoc(Document):
    """The final status of a request, and each change of status as ``[time, status]``."""

    status: str
    history: list[tuple[float, str]]


class ResultsDoc(Document):
    """The results of one simulation."""

    schema_version: str = SCHEMA_VERSION
    end_s: float
    requests: list[ClassDoc]
    hpcs: dict[str, UsageDoc]
    arcs: dict[str, UsageDoc]
    plmms: dict[str, PlmmDoc]
    epochs: EpochsDoc
    violations: dict[str, int]
    deviation_s: DistributionDoc
    lost_raw: int
    verification: VerificationDoc
    outcomes: dict[str, OutcomeDoc]
