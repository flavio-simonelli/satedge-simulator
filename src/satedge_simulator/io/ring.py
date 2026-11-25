"""Ring constellation: the builder that turns the parameters of a ring into a :class:`Constellation`.

Node names are ``COM<p>`` for the communication satellite of plane ``p`` (planes from 1), and
``P<p>-S<k>`` for the other satellites (``k`` from 0). Within a plane of three or more satellites
the intra-plane links form a cycle; a plane of two has one link; a plane of one has none.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.topology import (
    AlwaysAvailable,
    Constellation,
    GroundStation,
    Link,
    NodeId,
    Plane,
    Satellite,
    WindowedAvailability,
)
from satedge_simulator.errors import ScenarioError
from satedge_simulator.io.contact_plan import ContactPlan


@dataclass(frozen=True, slots=True)
class HpcSchedule:
    """Periodic computing windows of every satellite, in seconds.

    Attributes:
        period_s: Distance between the starts of two consecutive windows.
        duration_s: Length of each window, start-up of the containers included.
        startup_s: Part of each window spent starting the containers.
    """

    period_s: float = 5640.0
    duration_s: float = 300.0
    startup_s: float = 0.0

    def __post_init__(self) -> None:
        if not 0 < self.duration_s - self.startup_s <= self.period_s:
            raise ScenarioError(
                "la finestra dell'HPC (durata meno avvio) deve essere positiva e non più lunga "
                "del periodo"
            )

    @property
    def usable_s(self) -> float:
        """Length of each window once the containers are started."""
        return self.duration_s - self.startup_s


@dataclass(frozen=True, slots=True)
class LinkParams:
    """Capacity and latency of a family of links."""

    capacity_gbps: float = 1.0
    latency_s: float = 0.015


@dataclass(frozen=True, slots=True)
class RingSpec:
    """Parameters of a ring constellation.

    Attributes:
        planes: Number of planes.
        satellites_per_plane: Satellites in each plane.
        com_index: Position of the COM in each plane.
        horizon_s: The HPC windows are generated up to this instant.
        plmm_capacity_gb: PLMM capacity of every satellite.
        plmm_overrides_gb: PLMM capacity of some satellites, by node name.
        hpc: Computing windows of every satellite.
        hpc_phases_s: Start of the first window, by node name. Satellites not listed start
            equally spaced over the period, in plane order.
        hpc_rate_gbps: HPC-router rate of every satellite.
        intra_link: Parameters of the links inside a plane.
        inter_link: Parameters of the links between COMs.
        ground_link: Parameters of the links between COMs and the ground station.
        ground_station_id: Identifier of the ground station.
    """

    planes: int
    satellites_per_plane: int
    com_index: int
    horizon_s: float
    plmm_capacity_gb: float
    hpc_rate_gbps: float = 1.0
    plmm_overrides_gb: Mapping[NodeId, float] = field(
        default_factory=dict[NodeId, float]
    )
    hpc: HpcSchedule = field(default_factory=HpcSchedule)
    hpc_phases_s: Mapping[NodeId, float] = field(default_factory=dict[NodeId, float])
    intra_link: LinkParams = field(default_factory=LinkParams)
    inter_link: LinkParams = field(default_factory=LinkParams)
    ground_link: LinkParams = field(default_factory=LinkParams)
    ground_station_id: NodeId = "GS"

    def __post_init__(self) -> None:
        if self.planes < 1 or self.satellites_per_plane < 1:
            raise ScenarioError(
                "una costellazione ad anelli deve avere almeno un piano e un satellite"
            )
        if not 0 <= self.com_index < self.satellites_per_plane:
            raise ScenarioError(
                f"com_index {self.com_index} è fuori dall'intervallo per "
                f"{self.satellites_per_plane} satelliti per piano"
            )
        if not (math.isfinite(self.horizon_s) and self.horizon_s > 0):
            raise ScenarioError(
                f"l'orizzonte deve essere finito e > 0, invece è {self.horizon_s}"
            )


def node_name(plane: int, index: int, com_index: int) -> NodeId:
    """Name of the satellite at ``index`` in ``plane``."""
    return f"COM{plane}" if index == com_index else f"P{plane}-S{index}"


def ring_pairs(size: int) -> list[tuple[int, int]]:
    """Index pairs of the intra-plane links of a ring of ``size`` satellites."""
    if size == 1:
        return []
    if size == 2:
        return [(0, 1)]
    return [(k, (k + 1) % size) for k in range(size)]


def periodic_windows(phase_s: float, hpc: HpcSchedule, horizon_s: float) -> WindowSet:
    """Windows that start at ``phase_s`` and repeat every period, while they start before the horizon."""
    windows: list[Window] = []
    start = phase_s
    while start < horizon_s:
        windows.append(Window(start, start + hpc.usable_s))
        start += hpc.period_s
    return WindowSet(windows)


class RingConstellationBuilder:
    """Builds a :class:`Constellation` from a :class:`RingSpec` and a contact plan.

    The builder only assembles the parts: the naming, the phases of the computing windows and
    the link layout are computed by the functions of this module, so each can be read and tested
    on its own.
    """

    def __init__(self, spec: RingSpec, contact_plan: ContactPlan) -> None:
        self._spec = spec
        self._contact_plan = contact_plan
        self._names = {
            (p, k): node_name(p, k, spec.com_index)
            for p in range(1, spec.planes + 1)
            for k in range(spec.satellites_per_plane)
        }
        self._order = [self._names[key] for key in sorted(self._names)]
        self._check_overrides()

    def build(self) -> Constellation:
        """The constellation described by the spec."""
        planes = [self._plane(p) for p in range(1, self._spec.planes + 1)]
        ground = GroundStation(self._spec.ground_station_id)
        links = [
            *self._intra_links(),
            *self._inter_links(planes),
            *self._ground_links(planes, ground),
        ]
        return Constellation(planes, ground, links)

    def _check_overrides(self) -> None:
        known = set(self._order)
        for node in (*self._spec.plmm_overrides_gb, *self._spec.hpc_phases_s):
            if node not in known:
                raise ScenarioError(f"{node} non è un satellite dell'anello")

    def _plane(self, plane: int) -> Plane:
        satellites = tuple(
            self._satellite(plane, k) for k in range(self._spec.satellites_per_plane)
        )
        com = self._names[(plane, self._spec.com_index)]
        return Plane(plane, satellites, com)

    def _satellite(self, plane: int, index: int) -> Satellite:
        node = self._names[(plane, index)]
        spec = self._spec
        phase = spec.hpc_phases_s.get(node, self._default_phase(node))
        return Satellite(
            id=node,
            plmm_capacity_gb=spec.plmm_overrides_gb.get(node, spec.plmm_capacity_gb),
            hpc_rate_gbps=spec.hpc_rate_gbps,
            hpc_windows=periodic_windows(phase, spec.hpc, spec.horizon_s),
        )

    def _default_phase(self, node: NodeId) -> float:
        return self._order.index(node) * self._spec.hpc.period_s / len(self._order)

    def _intra_links(self) -> Iterator[Link]:
        n = self._spec.satellites_per_plane
        for p in range(1, self._spec.planes + 1):
            for i, j in ring_pairs(n):
                yield self._always_on(
                    self._names[(p, i)], self._names[(p, j)], self._spec.intra_link
                )

    def _inter_links(self, planes: list[Plane]) -> Iterator[Link]:
        coms = [plane.com for plane in planes]
        for i, a in enumerate(coms):
            for b in coms[i + 1 :]:
                yield self._windowed(a, b, self._spec.inter_link)

    def _ground_links(
        self, planes: list[Plane], ground: GroundStation
    ) -> Iterator[Link]:
        for plane in planes:
            yield self._windowed(plane.com, ground.id, self._spec.ground_link)

    @staticmethod
    def _always_on(a: NodeId, b: NodeId, params: LinkParams) -> Link:
        return Link(a, b, params.capacity_gbps, params.latency_s, AlwaysAvailable())

    def _windowed(self, a: NodeId, b: NodeId, params: LinkParams) -> Link:
        return Link(
            a,
            b,
            params.capacity_gbps,
            params.latency_s,
            WindowedAvailability(self._contact_plan.windows_of(a, b)),
        )
