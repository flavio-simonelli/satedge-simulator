"""Topology file: a ring constellation, read into a :class:`Constellation`."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from satedge_simulator.domain.topology import Constellation
from satedge_simulator.errors import DocumentError, ScenarioError
from satedge_simulator.io.base import Document, check_schema_version, read_document
from satedge_simulator.io.contact_plan import ContactPlan
from satedge_simulator.io.ring import (
    HpcSchedule,
    LinkParams,
    RingConstellationBuilder,
    RingSpec,
)


class TopologyKind(StrEnum):
    """The kinds of topology a file can describe."""

    RING_CONSTELLATION = "ring_constellation"


class TopologyHeader(BaseModel):
    """The fields every topology file has, read before the rest to choose the schema."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str
    kind: str

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


class HpcDoc(Document):
    """Computing windows of every satellite, in seconds."""

    period_s: float = 5640.0
    duration_s: float = 300.0
    startup_s: float = 0.0


class LinkDoc(Document):
    """Capacity and latency of a family of links."""

    capacity_gbps: float = 1.0
    latency_s: float = 0.015


class TopologyDoc(Document):
    """A topology file describing a ring constellation.

    The ground station is ``ground_station``; the satellites are named ``COM<p>`` and
    ``P<p>-S<k>``. The windows of the COM and ground links come from the contact plan.
    """

    schema_version: str
    kind: TopologyKind = TopologyKind.RING_CONSTELLATION
    ground_station: str = "GS"
    planes: int = 2
    satellites_per_plane: int = 9
    com_index: int = 0
    horizon_s: float
    plmm_capacity_gb: float
    plmm_overrides_gb: dict[str, float] = Field(default_factory=dict)
    hpc_rate_gbps: float = 1.0
    hpc: HpcDoc = Field(default_factory=HpcDoc)
    hpc_phases_s: dict[str, float] = Field(default_factory=dict)
    intra_link: LinkDoc = Field(default_factory=LinkDoc)
    inter_link: LinkDoc = Field(default_factory=LinkDoc)
    ground_link: LinkDoc = Field(default_factory=LinkDoc)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)

    def to_spec(self) -> RingSpec:
        """The parameters of the ring, as the builder needs them."""
        return RingSpec(
            planes=self.planes,
            satellites_per_plane=self.satellites_per_plane,
            com_index=self.com_index,
            horizon_s=self.horizon_s,
            plmm_capacity_gb=self.plmm_capacity_gb,
            hpc_rate_gbps=self.hpc_rate_gbps,
            plmm_overrides_gb=self.plmm_overrides_gb,
            hpc=HpcSchedule(self.hpc.period_s, self.hpc.duration_s, self.hpc.startup_s),
            hpc_phases_s=self.hpc_phases_s,
            intra_link=LinkParams(
                self.intra_link.capacity_gbps, self.intra_link.latency_s
            ),
            inter_link=LinkParams(
                self.inter_link.capacity_gbps, self.inter_link.latency_s
            ),
            ground_link=LinkParams(
                self.ground_link.capacity_gbps, self.ground_link.latency_s
            ),
            ground_station_id=self.ground_station,
        )


def load_topology(path: str | Path, contact_plan: ContactPlan) -> Constellation:
    """Read the topology in ``path`` and build the constellation, with the windows of ``contact_plan``.

    The ``kind`` field selects the schema and the builder. A kind that is not supported is an
    error that lists the supported ones.

    Raises:
        DocumentError: If the file cannot be read, its kind is not supported, it does not match
            the schema of its kind, or the topology it describes is not valid. The message
            names the file.
    """
    header = read_document(path, TopologyHeader)
    if header.kind == TopologyKind.RING_CONSTELLATION:
        return _load_ring(path, contact_plan)
    supported = ", ".join(kind.value for kind in TopologyKind)
    raise DocumentError(
        f"{path}: tipo di topologia non supportato {header.kind!r}, supportati: {supported}"
    )


def _load_ring(path: str | Path, contact_plan: ContactPlan) -> Constellation:
    document = read_document(path, TopologyDoc)
    try:
        return RingConstellationBuilder(document.to_spec(), contact_plan).build()
    except ScenarioError as error:
        raise DocumentError(f"{path}: {error}") from error
