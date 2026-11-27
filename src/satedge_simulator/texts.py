"""The texts the user reads, in Italian: names of the violations, the classes and the statistics."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from satedge_simulator.analysis.observations import Statistic
from satedge_simulator.domain.requests import Priority
from satedge_simulator.domain.violations import ViolationKind

VIOLATIONS: Mapping[ViolationKind, str] = MappingProxyType(
    {
        ViolationKind.DATA_NOT_READY: "dato non pronto",
        ViolationKind.HPC_BUSY: "HPC occupato",
        ViolationKind.LINK_BUSY: "link occupato",
        ViolationKind.PLMM_FULL: "PLMM piena",
        ViolationKind.HPC_WINDOW: "fuori dalla finestra di calcolo",
        ViolationKind.LINK_WINDOW: "fuori dalla finestra di visibilità",
        ViolationKind.PLAN_NOT_ARRIVED: "piano non ancora arrivato",
    }
)
"""The name of each kind of violation of the plan."""

PRIORITY_CLASSES: Mapping[Priority, str] = MappingProxyType(
    {Priority.URGENT: "urgenti", Priority.NON_URGENT: "non urgenti"}
)
"""The name of each priority class, as an adjective of the requests."""

STATISTICS: Mapping[Statistic, str] = MappingProxyType(
    {
        Statistic.RESPONSE: "tempo di risposta dal rilascio (s)",
        Statistic.ACCEPTANCE: "frazione di richieste accettate",
        Statistic.ON_TIME: "frazione di accettate consegnate in tempo",
        Statistic.HPC_UTILIZATION: "utilizzo degli HPC",
        Statistic.PLMM_OCCUPANCY: "occupazione totale delle PLMM (Gb)",
    }
)
"""The name of each statistic of the output analysis."""
