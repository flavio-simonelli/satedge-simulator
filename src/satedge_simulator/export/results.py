"""Results of a simulation, turned into the document that :mod:`satedge_simulator.io.results` writes.

This module knows the domain and the metrics; the document it builds knows nothing of them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from satedge_simulator.domain.lifecycle import RequestRecord
from satedge_simulator.io.results import (
    ClassDoc,
    DistributionDoc,
    EpochsDoc,
    FindingDoc,
    OutcomeDoc,
    PlmmDoc,
    ResultsDoc,
    UsageDoc,
    VerificationDoc,
)
from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.metrics.plmm import PlmmUsage
from satedge_simulator.metrics.requests import ClassMetrics
from satedge_simulator.metrics.resources import ResourceUsage
from satedge_simulator.metrics.summary import SimulationMetrics
from satedge_simulator.planning.adapters.scheduler.verification import AsRunFinding


def build_results(
    end_s: float,
    metrics: SimulationMetrics,
    records: Mapping[str, RequestRecord],
    findings: Iterable[AsRunFinding],
) -> ResultsDoc:
    """The results of a simulation: the metrics, the check of the as-run, and each request."""
    found = list(findings)
    return ResultsDoc(
        end_s=end_s,
        requests=[_class(c) for c in metrics.requests],
        hpcs={node: _usage(u) for node, u in metrics.hpcs.items()},
        arcs={f"{s}->{t}": _usage(u) for (s, t), u in metrics.arcs.items()},
        plmms={node: _plmm(u) for node, u in metrics.plmms.items()},
        epochs=EpochsDoc(
            epochs=metrics.epochs.epochs,
            new=metrics.epochs.new,
            accepted=metrics.epochs.accepted,
            rejected=metrics.epochs.rejected,
            solver_time_s=_distribution(metrics.epochs.solver_time),
            overruns=metrics.epochs.overruns,
            max_unreachable=metrics.epochs.max_unreachable,
        ),
        violations={kind.value: n for kind, n in metrics.violations.items()},
        deviation_s=_distribution(metrics.deviation),
        lost_raw=metrics.lost_raw,
        verification=VerificationDoc(
            passed=not found,
            findings=[
                FindingDoc(
                    epoch=f.epoch,
                    constraint=f.constraint,
                    request_id=f.request_id,
                    message=f.message,
                )
                for f in found
            ],
        ),
        outcomes={
            request_id: OutcomeDoc(
                status=record.status.value,
                history=[(at, status.value) for at, status in record.history],
            )
            for request_id, record in records.items()
        },
    )


def _class(c: ClassMetrics) -> ClassDoc:
    return ClassDoc(
        priority=c.priority.value,
        arrived=c.arrived,
        accepted=c.accepted,
        rejected=c.rejected,
        delivered_on_time=c.delivered_on_time,
        delivered_late=c.delivered_late,
        failed=c.failed,
        unfinished=c.unfinished,
        response_from_release_s=_distribution(c.response_from_release),
        response_from_arrival_s=_distribution(c.response_from_arrival),
        tardiness_s=_distribution(c.tardiness),
    )


def _usage(u: ResourceUsage) -> UsageDoc:
    return UsageDoc(
        busy_s=u.busy_s, available_s=u.available_s, utilization=u.utilization
    )


def _plmm(u: PlmmUsage) -> PlmmDoc:
    return PlmmDoc(
        capacity_gb=u.capacity_gb,
        peak_gb=u.peak_gb,
        mean_gb=u.mean_gb,
        peak_ratio=u.peak_ratio,
    )


def _distribution(d: Distribution) -> DistributionDoc:
    return DistributionDoc(count=d.count, mean=d.mean, p50=d.p50, p95=d.p95, max=d.max)
