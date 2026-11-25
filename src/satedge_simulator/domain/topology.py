"""Nodes and links of the constellation, and the container that validates them together."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.errors import ScenarioError

type NodeId = str


@dataclass(frozen=True, slots=True)
class AlwaysAvailable:
    """A link that is available at every instant, such as an intra-plane optical link."""


@dataclass(frozen=True, slots=True)
class WindowedAvailability:
    """A link that is available only in its visibility windows.

    Attributes:
        windows: The visibility windows, from the contact plan.
    """

    windows: WindowSet


type Availability = AlwaysAvailable | WindowedAvailability
"""When a link can carry data."""


def _require_positive_finite(value: float, what: str) -> None:
    if not (math.isfinite(value) and value > 0):
        raise ScenarioError(f"{what}: deve essere finito e > 0, invece è {value}")


@dataclass(frozen=True, slots=True)
class Satellite:
    """A satellite: it computes on its HPC, stores data in its PLMM and relays data.

    Attributes:
        id: Unique node identifier.
        plmm_capacity_gb: Net PLMM capacity available to the requests, in Gb.
        hpc_rate_gbps: Rate of the HPC-router link, the same in both directions, in Gbps.
        hpc_windows: Computing windows, net of the container start-up.
    """

    id: NodeId
    plmm_capacity_gb: float
    hpc_rate_gbps: float
    hpc_windows: WindowSet

    def __post_init__(self) -> None:
        if not self.id:
            raise ScenarioError("l'identificativo del satellite non può essere vuoto")
        _require_positive_finite(
            self.plmm_capacity_gb, f"{self.id}, capacità della PLMM"
        )
        _require_positive_finite(self.hpc_rate_gbps, f"{self.id}, velocità dell'HPC")

    def hpc_io_time(self, size_gb: float) -> float:
        """Seconds needed to read ``size_gb`` from the PLMM, or to write it there."""
        return size_gb / self.hpc_rate_gbps


@dataclass(frozen=True, slots=True)
class GroundStation:
    """The ground station: it receives the final outputs and never relays data.

    Attributes:
        id: Unique node identifier.
    """

    id: NodeId

    def __post_init__(self) -> None:
        if not self.id:
            raise ScenarioError(
                "l'identificativo della ground station non può essere vuoto"
            )


@dataclass(frozen=True, slots=True)
class Link:
    """A full-duplex link between two nodes.

    Both directions share the same capacity, latency and availability.

    Attributes:
        a: One endpoint.
        b: The other endpoint.
        capacity_gbps: Net capacity of each direction, in Gbps.
        latency_s: Propagation latency, in seconds.
        availability: When the link can carry data.
    """

    a: NodeId
    b: NodeId
    capacity_gbps: float
    latency_s: float
    availability: Availability

    def __post_init__(self) -> None:
        if self.a == self.b:
            raise ScenarioError(
                f"il link {self.a}-{self.b} collega un nodo a sé stesso"
            )
        _require_positive_finite(self.capacity_gbps, f"link {self.name}, capacità")
        _require_positive_finite(self.latency_s, f"link {self.name}, latenza")

    @property
    def name(self) -> str:
        """Readable name ``a-b``."""
        return f"{self.a}-{self.b}"

    @property
    def is_windowed(self) -> bool:
        """Whether the link is available only in its visibility windows."""
        return isinstance(self.availability, WindowedAvailability)

    def connects(self, x: NodeId, y: NodeId) -> bool:
        """Whether the link joins ``x`` and ``y``, in either order."""
        return {self.a, self.b} == {x, y}

    def transmission_time(self, size_gb: float) -> float:
        """Seconds needed to transmit ``size_gb`` on one direction of the link."""
        return size_gb / self.capacity_gbps


@dataclass(frozen=True, slots=True)
class Plane:
    """An orbital plane: its satellites and the one that talks to the other planes and to Earth.

    Attributes:
        id: Plane identifier, unique in the constellation.
        satellites: The satellites of the plane.
        com: Identifier of the communication satellite, one of ``satellites``.
    """

    id: int
    satellites: tuple[Satellite, ...]
    com: NodeId

    def __post_init__(self) -> None:
        if not self.satellites:
            raise ScenarioError(f"il piano {self.id} non ha satelliti")
        if self.com not in {s.id for s in self.satellites}:
            raise ScenarioError(
                f"piano {self.id}: il COM {self.com!r} non è uno dei suoi satelliti"
            )


class Constellation:
    """The whole network: planes, ground station and links, validated together.

    The constructor checks that the identifiers are unique, that every link joins known nodes,
    and that no pair of nodes is linked twice.
    """

    __slots__ = ("_ground", "_links", "_planes", "_satellites")

    def __init__(
        self,
        planes: Iterable[Plane],
        ground_station: GroundStation,
        links: Iterable[Link],
    ) -> None:
        self._planes = tuple(planes)
        self._ground = ground_station
        self._satellites = {s.id: s for p in self._planes for s in p.satellites}
        self._check_nodes()
        self._links = tuple(links)
        self._check_links()

    @property
    def planes(self) -> tuple[Plane, ...]:
        """The orbital planes, in declaration order."""
        return self._planes

    @property
    def ground_station(self) -> GroundStation:
        """The ground station."""
        return self._ground

    @property
    def links(self) -> tuple[Link, ...]:
        """All the links of the constellation."""
        return self._links

    @property
    def satellites(self) -> tuple[Satellite, ...]:
        """All the satellites, plane by plane."""
        return tuple(s for p in self._planes for s in p.satellites)

    def satellite(self, node: NodeId) -> Satellite:
        """The satellite with identifier ``node``."""
        try:
            return self._satellites[node]
        except KeyError:
            raise ScenarioError(f"satellite sconosciuto {node!r}") from None

    def is_satellite(self, node: NodeId) -> bool:
        """Whether ``node`` is a satellite."""
        return node in self._satellites

    def link_between(self, x: NodeId, y: NodeId) -> Link | None:
        """The link joining ``x`` and ``y``, or ``None`` if they are not linked."""
        return next((link for link in self._links if link.connects(x, y)), None)

    def _check_nodes(self) -> None:
        plane_ids = [p.id for p in self._planes]
        if len(set(plane_ids)) != len(plane_ids):
            raise ScenarioError(f"identificativi di piano duplicati {plane_ids}")
        satellite_ids = [s.id for p in self._planes for s in p.satellites]
        if len(set(satellite_ids)) != len(satellite_ids):
            raise ScenarioError("un identificativo di satellite è usato più volte")
        if self._ground.id in self._satellites:
            raise ScenarioError(
                f"l'identificativo della ground station {self._ground.id!r} è anche un satellite"
            )

    def _check_links(self) -> None:
        known = {*self._satellites, self._ground.id}
        seen: set[frozenset[NodeId]] = set()
        for link in self._links:
            for endpoint in (link.a, link.b):
                if endpoint not in known:
                    raise ScenarioError(
                        f"link {link.name}: nodo sconosciuto {endpoint!r}"
                    )
            pair = frozenset((link.a, link.b))
            if pair in seen:
                raise ScenarioError(f"il link {link.name} è dichiarato più volte")
            seen.add(pair)
