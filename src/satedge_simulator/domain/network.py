"""Network: the orbit planes, the ground station and the candidate links, checked together.

The network is the root of the topology: it is the only place that knows every node, so the
rules that span more than one object are checked here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from satedge_simulator.domain.ground_station import GroundStation
from satedge_simulator.domain.link import CandidateLink
from satedge_simulator.domain.orbit_plane import OrbitPlane
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.satellite import Satellite
from satedge_simulator.domain.terminal import LinkKind, Terminal
from satedge_simulator.errors import DomainError

type Node = Satellite | GroundStation
"""A node of the network: a satellite, or the ground station."""


@dataclass(frozen=True, slots=True, eq=False)
class Network:
    """The orbit planes, the ground station, and the links they can make.

    Built only if:
    - plane names, and the identifiers of all the nodes, are unique;
    - each satellite is in exactly one plane;
    - each terminal belongs to exactly one node;
    - each link joins terminals of two different nodes of the network;
    - an intra-orbit link joins two satellites of one plane, an inter-orbit link two
      satellites of different planes, a ground link a satellite and the ground station;
    - no two links join the same pair of terminals, in either order.

    Attributes:
        planes: The orbit planes, at least one.
        ground_station: The ground station.
        links: The candidate links.

    Raises:
        DomainError: If one of the rules is broken.
    """

    planes: tuple[OrbitPlane, ...]
    ground_station: GroundStation
    links: tuple[CandidateLink, ...]
    _plane_of: dict[Satellite, OrbitPlane] = field(init=False, repr=False)
    _node_of: dict[Terminal, Node] = field(init=False, repr=False)
    _links_of: dict[Node, tuple[CandidateLink, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Accept any iterable, and store tuples so the network stays immutable.
        object.__setattr__(self, "planes", tuple(self.planes))
        object.__setattr__(self, "links", tuple(self.links))
        if not self.planes:
            raise DomainError("the network must have at least one orbit plane")
        object.__setattr__(self, "_plane_of", self._index_planes())
        object.__setattr__(self, "_node_of", self._index_terminals())
        self._check_links()
        # After the checks, since it relies on every link joining two nodes of the network.
        object.__setattr__(self, "_links_of", self._index_links())

    # ---- queries -------------------------------------------------------------------

    @property
    def satellites(self) -> tuple[Satellite, ...]:
        """Every satellite, plane by plane."""
        return tuple(self._plane_of)

    def has(self, node: Node) -> bool:
        """Whether ``node`` is this very node of the network."""
        return node is self.ground_station or node in self._plane_of

    def plane_of(self, satellite: Satellite) -> OrbitPlane:
        """The plane of ``satellite``.

        Raises:
            DomainError: If the satellite is not in the network.
        """
        try:
            return self._plane_of[satellite]
        except KeyError:
            raise DomainError(
                f"satellite {satellite.id!r} is not in the network"
            ) from None

    def node_of(self, terminal: Terminal) -> Node:
        """The node that has ``terminal``.

        Raises:
            DomainError: If no node of the network has it.
        """
        try:
            return self._node_of[terminal]
        except KeyError:
            raise DomainError(
                "the terminal belongs to no node of the network"
            ) from None

    def links_of(self, node: Node) -> tuple[CandidateLink, ...]:
        """The candidate links that have one end on ``node``, in the order of ``links``.

        Raises:
            DomainError: If the node is not in the network.
        """
        try:
            return self._links_of[node]
        except KeyError:
            raise DomainError(f"node {node.id!r} is not in the network") from None

    def require_request(self, request: RequestSpec) -> None:
        """Check that ``request`` can run on this network.

        Every request obeys this rule, whether it is written in advance or generated.

        Raises:
            DomainError: If its origin is not a satellite of the network.
        """
        if not self.has(request.origin):
            raise DomainError(
                f"request {request.id!r} starts from satellite {request.origin.id!r}, "
                "which is not in the network"
            )

    # ---- checks --------------------------------------------------------------------

    def _index_planes(self) -> dict[Satellite, OrbitPlane]:
        names: set[str] = set()
        ids: set[str] = {self.ground_station.id}
        plane_of: dict[Satellite, OrbitPlane] = {}
        for plane in self.planes:
            if plane.name in names:
                raise DomainError(f"the plane name {plane.name!r} is used twice")
            names.add(plane.name)
            for satellite in plane.satellites:
                if satellite in plane_of:
                    raise DomainError(
                        f"satellite {satellite.id!r} is in both plane "
                        f"{plane_of[satellite].name!r} and plane {plane.name!r}"
                    )
                if satellite.id in ids:
                    raise DomainError(
                        f"the node identifier {satellite.id!r} is used twice"
                    )
                ids.add(satellite.id)
                plane_of[satellite] = plane
        return plane_of

    def _index_terminals(self) -> dict[Terminal, Node]:
        owners: list[tuple[Node, tuple[Terminal, ...]]] = [
            (satellite, satellite.oct.terminals) for satellite in self._plane_of
        ]
        owners.append((self.ground_station, self.ground_station.antennas))
        node_of: dict[Terminal, Node] = {}
        for node, terminals in owners:
            for terminal in terminals:
                other = node_of.get(terminal)
                if other is not None:
                    raise DomainError(
                        f"a terminal belongs to both {other.id!r} and {node.id!r}"
                    )
                node_of[terminal] = node
        return node_of

    def _index_links(self) -> dict[Node, tuple[CandidateLink, ...]]:
        # Every node has an entry, even with no link.
        nodes: tuple[Node, ...] = (*self._plane_of, self.ground_station)
        links_of: dict[Node, list[CandidateLink]] = {node: [] for node in nodes}
        for link in self.links:
            links_of[self._node_of[link.a]].append(link)
            links_of[self._node_of[link.b]].append(link)
        return {node: tuple(links) for node, links in links_of.items()}

    def _check_links(self) -> None:
        seen: set[frozenset[Terminal]] = set()
        for link in self.links:
            self._check_link(link)
            ends = frozenset((link.a, link.b))
            if ends in seen:
                a, b = self._node_of[link.a], self._node_of[link.b]
                raise DomainError(
                    f"two links {a.id!r}-{b.id!r} join the same pair of terminals"
                )
            seen.add(ends)

    def _check_link(self, link: CandidateLink) -> None:
        a, b = self._node_of.get(link.a), self._node_of.get(link.b)
        if a is None or b is None:
            raise DomainError(
                "a candidate link uses a terminal of no node of the network"
            )
        if a is b:
            raise DomainError(f"a candidate link joins two terminals of {a.id!r}")
        kind = link.a.kind
        if kind is LinkKind.GROUND:
            if a is not self.ground_station and b is not self.ground_station:
                raise DomainError(
                    f"the ground link {a.id!r}-{b.id!r} does not reach the ground station"
                )
            return
        if not (isinstance(a, Satellite) and isinstance(b, Satellite)):
            raise DomainError(
                f"the {kind} link {a.id!r}-{b.id!r} must join two satellites"
            )
        same_plane = self._plane_of[a] is self._plane_of[b]
        if kind is LinkKind.INTRA_ORBIT and not same_plane:
            raise DomainError(
                f"the intra-orbit link {a.id!r}-{b.id!r} joins satellites of different planes"
            )
        if kind is LinkKind.INTER_ORBIT and same_plane:
            raise DomainError(
                f"the inter-orbit link {a.id!r}-{b.id!r} joins satellites of one plane"
            )
