"""Satellites file: the types of satellite of the scenario, with their memory, HPC and antennas."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from satedge_simulator.io.availability import AvailabilityDoc, PeriodicDoc
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
    """The HPC of a satellite: its router rate, its memory, its start-up, and when it is available.

    ``startup_s`` is the part of each availability spent starting the containers. It must be
    shorter than a periodic availability, so that some of it is left to compute.
    """

    rate_gbps: float = Field(gt=0)
    memory_gb: float = Field(gt=0)
    startup_s: float = Field(default=0, ge=0)
    availability: AvailabilityDoc

    @model_validator(mode="after")
    def _startup_leaves_time_to_compute(self) -> HpcDoc:
        if (
            isinstance(self.availability, PeriodicDoc)
            and self.startup_s >= self.availability.duration_s
        ):
            raise ValueError(
                "startup_s must be shorter than the duration of the availability"
            )
        return self


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
