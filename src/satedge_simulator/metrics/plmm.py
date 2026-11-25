"""Occupation of the PLMMs: peak and mean over time."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from satedge_simulator.domain.topology import Constellation, NodeId
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import PlmmChanged


@dataclass(frozen=True, slots=True)
class PlmmUsage:
    """The occupied memory of one PLMM, over the simulation.

    Attributes:
        capacity_gb: Net capacity of the PLMM.
        peak_gb: Highest occupied memory.
        mean_gb: Occupied memory averaged over time, from 0 to the end.
    """

    capacity_gb: float
    peak_gb: float
    mean_gb: float

    @property
    def peak_ratio(self) -> float:
        """``peak_gb / capacity_gb``."""
        return self.peak_gb / self.capacity_gb


class PlmmCollector:
    """Integrates the level of each PLMM over time, from the notifications of the runtime."""

    def __init__(self, constellation: Constellation) -> None:
        self._constellation = constellation
        self._level: dict[NodeId, tuple[float, float]] = {}  # (since, level)
        self._area: dict[NodeId, float] = {}
        self._peak: dict[NodeId, float] = {}

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(PlmmChanged, self._changed)

    def usage(self, end_s: float) -> Mapping[NodeId, PlmmUsage]:
        """The occupation of the PLMM of each satellite, until ``end_s``."""
        usage: dict[NodeId, PlmmUsage] = {}
        for satellite in self._constellation.satellites:
            since, level = self._level.get(satellite.id, (0.0, 0.0))
            area = self._area.get(satellite.id, 0.0) + level * max(0.0, end_s - since)
            usage[satellite.id] = PlmmUsage(
                capacity_gb=satellite.plmm_capacity_gb,
                peak_gb=self._peak.get(satellite.id, 0.0),
                mean_gb=area / end_s,
            )
        return usage

    def _changed(self, n: PlmmChanged) -> None:
        since, level = self._level.get(n.satellite, (0.0, 0.0))
        self._area[n.satellite] = self._area.get(n.satellite, 0.0) + level * (
            n.time - since
        )
        self._level[n.satellite] = (n.time, n.level_gb)
        self._peak[n.satellite] = max(self._peak.get(n.satellite, 0.0), n.level_gb)
