"""Topology file: the ground station, the orbital planes with their satellites, and the links.

The schemas of this module describe how the file is written: the names of the fields, their types,
and which of them are required. Unknown fields are errors. Whether a value is meaningful, such as
the sign of a time or of a rate, is not checked here: it is an invariant of the domain.

The names that refer to another file are not checked here either: the type of a satellite is
checked against the satellites file when the network is built, by
:func:`~satedge_simulator.io.loading.topology.build_network`.
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
    """A satellite of a periodic plane whose HPC follows the period of the plane.

    The HPC has one window in each period, and all the windows have the same length.

    Attributes:
        name: Name of the satellite.
        type: Name of its type, as the satellites file defines it.
        first_start_s: Instant the first window of the HPC opens, in seconds.
        duration_s: Length of each window of the HPC, in seconds.
    """

    name: str
    type: str
    first_start_s: float
    duration_s: float


class ListedNodeDoc(Document):
    """A satellite whose HPC windows are listed one by one, on a plane of either kind.

    Attributes:
        name: Name of the satellite.
        type: Name of its type, as the satellites file defines it.
        hpc_windows: The windows of the HPC.
    """

    name: str
    type: str
    hpc_windows: list[WindowDoc]


class GroundAntennaDoc(Document):
    """One antenna of the ground station.

    Attributes:
        rate_gbps: Rate of the antenna, in Gbps.
    """

    rate_gbps: float


class GroundStationDoc(Document):
    """The ground station.

    Attributes:
        name: Name of the station, which the links use to refer to it.
        antennas: The antennas of the station.
    """

    name: str
    antennas: list[GroundAntennaDoc]


class PeriodicPlaneDoc(Document):
    """A plane that states the period of its orbit.

    Each satellite either gives the phase and the length of its HPC windows, which repeat with
    this period, or lists its windows, to which the period does not apply.

    Attributes:
        name: Name of the plane.
        kind: Always ``periodic``.
        period_s: Period of the orbit, in seconds.
        nodes: The satellites of the plane, each in either of the two forms.
    """

    name: str
    kind: Literal[AvailabilityKind.PERIODIC]
    period_s: float
    nodes: list[PhasedNodeDoc | ListedNodeDoc]


class ListedPlaneDoc(Document):
    """A plane with no period: each of its satellites lists its HPC windows.

    Attributes:
        name: Name of the plane.
        kind: Always ``windows``.
        nodes: The satellites of the plane.
    """

    name: str
    kind: Literal[AvailabilityKind.WINDOWS]
    nodes: list[ListedNodeDoc]


PlaneDoc = Annotated[PeriodicPlaneDoc | ListedPlaneDoc, Field(discriminator="kind")]
"""A plane of either form. Its ``kind`` field says which one."""


class LinkDoc(Document):
    """A link between two nodes. A node is a satellite or the ground station.

    Attributes:
        a: Name of one node.
        b: Name of the other node.
        latency_s: Propagation latency of the link, in seconds.
        availability: When the link is available: always, periodically, or in listed windows.
    """

    a: str
    b: str
    latency_s: float
    availability: AvailabilityDoc


class TopologyDoc(VersionedDocument):
    """The content of a topology file.

    Attributes:
        schema_version: Version of the format of the file.
        ground_station: The ground station.
        planes: The orbital planes.
        links: The links between the nodes. It may be left out: there are then no links.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    ground_station: GroundStationDoc
    planes: list[PlaneDoc]
    links: list[LinkDoc] = Field(default_factory=list)


def read_topology(path: str | Path) -> TopologyDoc:
    """Read the topology file in ``path`` and validate it against :class:`TopologyDoc`.

    Raises:
        DocumentError: If the format is unknown, the file cannot be read, its text is not valid
            in its format, it does not match the schema, or its version is not supported. The
            message names the file.
    """
    return read_document(path, TopologyDoc)
