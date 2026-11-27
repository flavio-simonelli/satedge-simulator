"""Satellites file: the types of satellite, each with its PLMM, its HPC and its antennas.

The values are not checked here: whether they are meaningful is an invariant of the domain.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from satedge_simulator.io.base import Document, VersionedDocument, read_document


class LinkKind(StrEnum):
    """The kind of link an antenna serves, as the satellites file spells it."""

    INTRA_ORBIT = "intra_orbit"
    INTER_ORBIT = "inter_orbit"
    GROUND = "ground"


class AntennaDoc(Document):
    """One antenna of a satellite type.

    Attributes:
        link: The kind of link the antenna serves.
        rate_gbps: Rate of the antenna, in Gbps.
    """

    link: LinkKind
    rate_gbps: float


class PlmmDoc(Document):
    """The PLMM of a satellite type.

    Attributes:
        capacity_gb: Capacity of the PLMM.
    """

    capacity_gb: float


class HpcDoc(Document):
    """The HPC of a satellite type. When it is available is written in the topology file.

    Attributes:
        rate_gbps: Rate of the router of the HPC, in Gbps.
        memory_gb: Memory of the HPC.
    """

    rate_gbps: float
    memory_gb: float


class SatelliteTypeDoc(Document):
    """One type of satellite.

    Attributes:
        description: Text for people reading the file.
        plmm: The PLMM.
        hpc: The HPC.
        antennas: The antennas.
    """

    description: str
    plmm: PlmmDoc
    hpc: HpcDoc
    antennas: list[AntennaDoc]


class SatellitesDoc(VersionedDocument):
    """The content of a satellites file.

    Attributes:
        schema_version: Version of the format of the file.
        satellite_types: The types of satellite, by name.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    satellite_types: dict[str, SatelliteTypeDoc]


def load_satellites(path: str | Path) -> dict[str, SatelliteTypeDoc]:
    """Read the satellite types in ``path``, by name.

    Raises:
        DocumentError: If the format is unknown, the file cannot be read, its text is not valid
            in its format, it does not match the schema, or its version is not supported. The
            message names the file.
    """
    return dict(read_document(path, SatellitesDoc).satellite_types)
