"""Topology file: the planes of the constellation, their satellites, and the links between them.

A plane is an orbit, even one with a single satellite. Each satellite of a plane has the type of
a satellite of the satellites file. A link is between two nodes, which are satellites or the
ground station, and each link states its availability. A plane with ``ring: true`` links its
satellites in a cycle, always available, so those links need not be written.
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


class PlaneDoc(Document):
    """A plane, that is an orbit, with its satellites.

    ``ring``: whether the satellites are linked in a cycle, in the order they are listed, with
    links that are always available. A plane of two satellites has one such link; a plane of one
    has none.
    """

    name: str
    ring: bool = False
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


def _ring_pairs(names: list[str]) -> list[frozenset[str]]:
    """The node pairs linked by a ring over ``names``, in the order they are listed."""
    if len(names) < 2:
        return []
    if len(names) == 2:
        return [frozenset(names)]
    return [
        frozenset((names[k], names[(k + 1) % len(names)])) for k in range(len(names))
    ]


class TopologyDoc(VersionedDocument):
    """A topology file: the planes, the ground station, and the links with their availability."""

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    ground_station: str
    planes: list[PlaneDoc] = Field(min_length=1)
    links: list[LinkDoc] = Field(default_factory=list)

    @model_validator(mode="after")
    def _links_refer_to_known_nodes(self) -> TopologyDoc:
        names = [node.name for plane in self.planes for node in plane.nodes]
        if len(set(names)) != len(names):
            raise ValueError("node names must be unique across the planes")
        if self.ground_station in names:
            raise ValueError(
                f"the ground station {self.ground_station!r} is also a satellite"
            )
        known = {*names, self.ground_station}
        for link in self.links:
            for end in (link.a, link.b):
                if end not in known:
                    raise ValueError(
                        f"link {link.a}-{link.b} refers to unknown node {end!r}"
                    )
        implicit = {
            pair
            for plane in self.planes
            if plane.ring
            for pair in _ring_pairs([node.name for node in plane.nodes])
        }
        seen: set[frozenset[str]] = set()
        for link in self.links:
            pair = frozenset((link.a, link.b))
            if pair in seen or pair in implicit:
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
