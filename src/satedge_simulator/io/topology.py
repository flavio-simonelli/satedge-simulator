"""Topology file: the planes of the constellation, their satellites, and the links between them.

A plane is an orbit, even one with a single satellite. Each satellite of a plane has the type of
a satellite of the satellites file. A link is between two nodes, which are satellites or the
ground station, and each link states its availability. Every link is written, even the ones
that join neighbours of a plane.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from satedge_simulator.io.availability import AvailabilityDoc
from satedge_simulator.io.base import Document, VersionedDocument, read_document


class NodeDoc(Document):
    """A satellite of a plane: its name, and the type it has in the satellites file."""

    name: str
    type: str


class GroundAntennaDoc(Document):
    """One antenna of the ground station: its rate. It links to any satellite that has one."""

    rate_gbps: float = Field(gt=0)


class GroundStationDoc(Document):
    """The ground station: the node that the links to the ground join.

    Each antenna limits how many links the station carries at once.
    """

    name: str
    antennas: list[GroundAntennaDoc] = Field(min_length=1)


class PlaneDoc(Document):
    """A plane, that is an orbit, with its satellites."""

    name: str
    nodes: list[NodeDoc] = Field(min_length=1)


class LinkDoc(Document):
    """A link between two nodes, and when it is available."""

    a: str
    b: str
    availability: AvailabilityDoc

    @model_validator(mode="after")
    def _two_different_nodes(self) -> LinkDoc:
        if self.a == self.b:
            raise ValueError(
                f"a link joins two different nodes, but both are {self.a!r}"
            )
        return self


class TopologyDoc(VersionedDocument):
    """A topology file: the planes, the ground station, and the links with their availability."""

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    ground_station: GroundStationDoc
    planes: list[PlaneDoc] = Field(min_length=1)
    links: list[LinkDoc] = Field(default_factory=list)

    @model_validator(mode="after")
    def _links_refer_to_known_nodes(self) -> TopologyDoc:
        names = [node.name for plane in self.planes for node in plane.nodes]
        if len(set(names)) != len(names):
            raise ValueError("node names must be unique across the planes")
        ground = self.ground_station.name
        if ground in names:
            raise ValueError(f"the ground station {ground!r} is also a satellite")
        known = {*names, ground}
        for link in self.links:
            for end in (link.a, link.b):
                if end not in known:
                    raise ValueError(
                        f"link {link.a}-{link.b} refers to unknown node {end!r}"
                    )
        seen: set[frozenset[str]] = set()
        for link in self.links:
            pair = frozenset((link.a, link.b))
            if pair in seen:
                raise ValueError(f"link {link.a}-{link.b} is declared more than once")
            seen.add(pair)
        return self


def read_topology(path: str | Path) -> TopologyDoc:
    """Read and validate the topology file in ``path``.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema. The message
            names the file.
    """
    return read_document(path, TopologyDoc)
