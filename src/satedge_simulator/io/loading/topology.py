"""Topology mapping: the topology and satellites documents, turned into the network.

Each satellite is built from its type, with terminals of its own. The input states links between
nodes: one such link becomes a candidate link between terminals for each pair of compatible
terminals of the two nodes. The kind of link is deduced from the nodes, not written in the input.

The files already use the units of the domain (seconds, Gb, Gbps): each number only has to become
the quantity of its unit.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from satedge_simulator.domain.availability import Availability
from satedge_simulator.domain.ground_station import GroundStation
from satedge_simulator.domain.link import CandidateLink, ConstantLatency, Latency
from satedge_simulator.domain.network import Network, Node
from satedge_simulator.domain.orbit_plane import OrbitPlane
from satedge_simulator.domain.quantities import DataSize, Duration, Rate
from satedge_simulator.domain.satellite import (
    HpcModule,
    OctModule,
    PlmmModule,
    Satellite,
)
from satedge_simulator.domain.terminal import LinkKind, Terminal
from satedge_simulator.errors import DocumentError, DomainError
from satedge_simulator.io.loading.availability import availability, periodic, scheduled
from satedge_simulator.io.loading.errors import errors_in
from satedge_simulator.io.satellites import SatelliteTypeDoc
from satedge_simulator.io.topology import (
    GroundStationDoc,
    LinkDoc,
    ListedNodeDoc,
    PeriodicPlaneDoc,
    PhasedNodeDoc,
    PlaneDoc,
    TopologyDoc,
)


def build_network(
    topology: TopologyDoc,
    satellite_types: Mapping[str, SatelliteTypeDoc],
    topology_file: Path,
    satellites_file: Path,
) -> Network:
    """The network that the documents describe.

    The two paths are used by the error messages only.

    Raises:
        DocumentError: If a satellite has a type that ``satellite_types`` does not define, a
            link names an unknown node, or a value breaks a rule of the domain. The message
            names the file that holds the value.
    """
    planes = tuple(
        _plane(doc, satellite_types, topology_file, satellites_file)
        for doc in topology.planes
    )
    with errors_in(topology_file, "ground station"):
        station = _ground_station(topology.ground_station)

    # A name used twice keeps one node here: the network then rejects it.
    nodes: dict[str, Node] = {s.id: s for plane in planes for s in plane.satellites}
    nodes[station.id] = station

    links: list[CandidateLink] = []
    for doc in topology.links:
        links.extend(_links(doc, nodes, planes, topology_file))

    with errors_in(topology_file, "network"):
        return Network(planes, station, tuple(links))


def terminal_links_between(
    a: Node,
    b: Node,
    latency: Latency,
    link_availability: Availability,
    planes: Iterable[OrbitPlane],
) -> tuple[CandidateLink, ...]:
    """The candidate links between two nodes: one for each pair of compatible terminals.

    The kind is intra-orbit within a plane, inter-orbit between planes, and ground for a link to
    the ground station. Every candidate shares the latency and the availability of the link
    between the nodes.

    Raises:
        DomainError: If the nodes are the same, or if one of them has no terminal of the kind.
    """
    if a is b:
        raise DomainError(f"a link joins two different nodes, but both are {a.id!r}")
    kind = _kind(a, b, tuple(planes))
    ends_a, ends_b = _terminals(a, kind), _terminals(b, kind)
    for node, ends in ((a, ends_a), (b, ends_b)):
        if not ends:
            raise DomainError(f"node {node.id!r} has no terminal of kind {kind}")
    return tuple(
        CandidateLink(x, y, latency, link_availability) for x in ends_a for y in ends_b
    )


def _plane(
    doc: PlaneDoc,
    satellite_types: Mapping[str, SatelliteTypeDoc],
    topology_file: Path,
    satellites_file: Path,
) -> OrbitPlane:
    period_s = doc.period_s if isinstance(doc, PeriodicPlaneDoc) else None
    for node in doc.nodes:
        if node.type not in satellite_types:
            raise DocumentError(
                f"{topology_file}: satellite {node.name!r}: the type {node.type!r} is not "
                f"defined in {satellites_file}"
            )
    satellites = tuple(
        _satellite(
            node,
            period_s,
            satellite_types[node.type],
            topology_file,
            satellites_file,
        )
        for node in doc.nodes
    )
    with errors_in(topology_file, f"plane {doc.name!r}"):
        return OrbitPlane(doc.name, satellites)


def _satellite(
    node: PhasedNodeDoc | ListedNodeDoc,
    period_s: float | None,
    kind: SatelliteTypeDoc,
    topology_file: Path,
    satellites_file: Path,
) -> Satellite:
    """The satellite of ``node``, of the type ``kind``, with new terminals.

    ``period_s`` is the period of its plane, ``None`` for a plane that has none.
    """
    what = f"satellite {node.name!r}"
    with errors_in(topology_file, what):
        if isinstance(node, ListedNodeDoc):
            hpc_availability: Availability = scheduled(node.hpc_windows)
        else:
            # The schema admits a phased satellite on a periodic plane only.
            assert period_s is not None
            hpc_availability = periodic(node.first_start_s, period_s, node.duration_s)

    # Built again for each satellite: two satellites never share a terminal.
    with errors_in(satellites_file, f"satellite type {node.type!r}"):
        plmm = PlmmModule(DataSize(kind.plmm.capacity_gb))
        hpc = HpcModule(
            Rate(kind.hpc.rate_gbps),
            DataSize(kind.hpc.memory_gb),
            hpc_availability,
        )
        oct_module = OctModule(
            tuple(
                Terminal(LinkKind(antenna.link.value), Rate(antenna.rate_gbps))
                for antenna in kind.antennas
            )
        )

    with errors_in(topology_file, what):
        return Satellite(node.name, plmm, hpc, oct_module)


def _ground_station(doc: GroundStationDoc) -> GroundStation:
    return GroundStation(
        doc.name,
        tuple(Terminal(LinkKind.GROUND, Rate(a.rate_gbps)) for a in doc.antennas),
    )


def _links(
    doc: LinkDoc,
    nodes: Mapping[str, Node],
    planes: tuple[OrbitPlane, ...],
    topology_file: Path,
) -> tuple[CandidateLink, ...]:
    what = f"link {doc.a!r}-{doc.b!r}"
    for name in (doc.a, doc.b):
        if name not in nodes:
            raise DocumentError(
                f"{topology_file}: {what}: {name!r} is neither a satellite nor the "
                "ground station"
            )
    with errors_in(topology_file, what):
        return terminal_links_between(
            nodes[doc.a],
            nodes[doc.b],
            ConstantLatency(Duration(doc.latency_s)),
            availability(doc.availability),
            planes,
        )


def _plane_of(node: Satellite, planes: Iterable[OrbitPlane]) -> OrbitPlane | None:
    return next((p for p in planes if node in p.satellites), None)


def _kind(a: Node, b: Node, planes: tuple[OrbitPlane, ...]) -> LinkKind:
    if isinstance(a, GroundStation) or isinstance(b, GroundStation):
        return LinkKind.GROUND
    plane = _plane_of(a, planes)
    if plane is not None and plane is _plane_of(b, planes):
        return LinkKind.INTRA_ORBIT
    return LinkKind.INTER_ORBIT


def _terminals(node: Node, kind: LinkKind) -> tuple[Terminal, ...]:
    pool = node.antennas if isinstance(node, GroundStation) else node.oct.terminals
    return tuple(t for t in pool if t.kind is kind)
