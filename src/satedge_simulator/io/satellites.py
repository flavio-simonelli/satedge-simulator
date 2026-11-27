"""Satellites file: the types of satellite of the scenario, with their memory, HPC and antennas."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from pydantic import Field

from satedge_simulator.io.base import Document, VersionedDocument, read_document


class LinkKind(StrEnum):
    """The kind of link an antenna serves, as the satellites file spells it."""

    INTRA_ORBIT = "intra_orbit"
    INTER_ORBIT = "inter_orbit"
    GROUND = "ground"


class AntennaDoc(Document):
    """One antenna: the kind of link it serves, and its rate."""

    link: LinkKind
    rate_gbps: float = Field(gt=0)


class PlmmDoc(Document):
    """The PLMM of a satellite: its capacity."""

    capacity_gb: float = Field(gt=0)


class HpcDoc(Document):
    """The HPC of a satellite type: its router rate and its memory.

    When the HPC is available comes from the plane, and the start-up of its containers from each
    satellite, in the topology file.
    """

    rate_gbps: float = Field(gt=0)
    memory_gb: float = Field(gt=0)


class SatelliteTypeDoc(Document):
    """One type of satellite, with its PLMM, its HPC and its antennas."""

    description: str
    plmm: PlmmDoc
    hpc: HpcDoc
    antennas: list[AntennaDoc] = Field(min_length=1)


class SatellitesDoc(VersionedDocument):
    """A satellites file: the types of satellite, by name."""

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    satellite_types: dict[str, SatelliteTypeDoc]


def load_satellites(path: str | Path) -> dict[str, SatelliteTypeDoc]:
    """Read the satellite types in ``path``, by name.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema. The message
            names the file.
    """
    return dict(read_document(path, SatellitesDoc).satellite_types)
