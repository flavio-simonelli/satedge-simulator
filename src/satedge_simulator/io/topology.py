"""Topology file: the planes of the constellation, their satellites, and the links between them.

A plane is an orbit, even one with a single satellite. Each satellite of a plane has the type of
a satellite of the satellites file. A link is between two nodes, which are satellites or the
ground station, and each link states its availability. Every link is written, even the ones
that join neighbours of a plane.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, ClassVar, Literal

from pydantic import Field

from satedge_simulator.io.availability import (
    AvailabilityDoc,
    AvailabilityKind,
    WindowDoc,
)
from satedge_simulator.io.base import Document, VersionedDocument, read_document


class PhasedNodeDoc(Document):
    """A satellite of a periodic plane: its name, its type, and its phase in the orbit.

    ``first_start_s`` is the instant the first window of its HPC opens. The other windows follow
    every period of the plane.
    """

    name: str
    type: str
    first_start_s: float = Field(ge=0)


class ListedNodeDoc(Document):
    """A satellite of a plane whose HPC windows are listed: its name, its type, and its windows."""

    name: str
    type: str
    hpc_windows: list[WindowDoc]


class GroundAntennaDoc(Document):
    """One antenna of the ground station: its rate. It links to any satellite that has one."""

    rate_gbps: float = Field(gt=0)


class GroundStationDoc(Document):
    """The ground station: the node that the links to the ground join.

    Each antenna limits how many links the station carries at once.
    """

    name: str
    antennas: list[GroundAntennaDoc] = Field(min_length=1)


class PeriodicPlaneDoc(Document):
    """A plane whose HPCs open periodically: period and duration are those of the orbit, written
    once, here.

    Each satellite follows that period from its own ``first_start_s``, or, if it gives its own
    ``hpc_windows`` instead, its HPC uses those windows and the period does not apply to it.
    """

    name: str
    kind: Literal[AvailabilityKind.PERIODIC]
    period_s: float = Field(gt=0)
    duration_s: float = Field(gt=0)
    nodes: list[PhasedNodeDoc | ListedNodeDoc] = Field(min_length=1)


class ListedPlaneDoc(Document):
    """A plane whose HPC windows are not periodic: each satellite lists its own windows."""

    name: str
    kind: Literal[AvailabilityKind.WINDOWS]
    nodes: list[ListedNodeDoc] = Field(min_length=1)


PlaneDoc = Annotated[PeriodicPlaneDoc | ListedPlaneDoc, Field(discriminator="kind")]
"""A plane: its kind tells whether its satellites give a phase or their own windows."""


class LinkDoc(Document):
    """A link between two nodes, and when it is available."""

    a: str
    b: str
    availability: AvailabilityDoc


class TopologyDoc(VersionedDocument):
    """A topology file: the planes, the ground station, and the links with their availability."""

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    ground_station: GroundStationDoc
    planes: list[PlaneDoc] = Field(min_length=1)
    links: list[LinkDoc] = Field(default_factory=list)


def read_topology(path: str | Path) -> TopologyDoc:
    """Read and validate the topology file in ``path``.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema. The message
            names the file.
    """
    return read_document(path, TopologyDoc)
