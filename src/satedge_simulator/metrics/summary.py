"""The indicators of a whole simulation, in one record."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from satedge_simulator.domain.lifecycle import RequestRecord
from satedge_simulator.domain.plan import EpochPlan
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.metrics.as_run import AsRun
from satedge_simulator.metrics.distribution import Distribution
from satedge_simulator.metrics.epochs import EpochCollector, EpochMetrics
from satedge_simulator.metrics.plmm import PlmmCollector, PlmmUsage
from satedge_simulator.metrics.requests import ClassMetrics, request_metrics
from satedge_simulator.metrics.resources import Arc, ResourceCollector, ResourceUsage


@dataclass(frozen=True, slots=True)
class SimulationMetrics:
    """The indicators of a simulation.

    Attributes:
        requests: The requests of each priority class, urgent first.
        hpcs: Use of the HPC of each satellite.
        arcs: Use of each direction of each link.
        plmms: Occupation of the PLMM of each satellite.
        epochs: The planning epochs.
        violations: Violations of the plan, by kind.
        deviation: Gap between the actual and the planned start of each executed action.
        lost_raw: Requests whose raw data did not fit in the PLMM of their origin.
    """

    requests: tuple[ClassMetrics, ...]
    hpcs: Mapping[NodeId, ResourceUsage]
    arcs: Mapping[Arc, ResourceUsage]
    plmms: Mapping[NodeId, PlmmUsage]
    epochs: EpochMetrics
    violations: Mapping[ViolationKind, int]
    deviation: Distribution
    lost_raw: int


def summarize(
    end_s: float,
    requests: Iterable[RequestSpec],
    records: Mapping[str, RequestRecord],
    violations: Iterable[Violation],
    plans: Iterable[EpochPlan],
    as_run: AsRun,
    resources: ResourceCollector,
    plmms: PlmmCollector,
    epochs: EpochCollector,
    lost_raw: int,
) -> SimulationMetrics:
    """Compose the indicators of a simulation that ended at ``end_s``."""
    by_kind = Counter(v.kind for v in violations)
    return SimulationMetrics(
        requests=request_metrics(records, requests),
        hpcs=MappingProxyType(dict(resources.hpcs(end_s))),
        arcs=MappingProxyType(dict(resources.arcs(end_s))),
        plmms=MappingProxyType(dict(plmms.usage(end_s))),
        epochs=epochs.metrics(),
        violations=MappingProxyType(
            {k: by_kind[k] for k in ViolationKind if by_kind[k]}
        ),
        deviation=as_run.deviation(plans),
        lost_raw=lost_raw,
    )
