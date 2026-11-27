"""Satellite: the node that computes, stores data and relays it, made of three modules.

- the HPC computes on the data, during its computing windows;
- the PLMM stores the data of the requests, up to its capacity;
- the OCT is the set of terminals that link the satellite to the other nodes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.errors import DomainError


class LinkKind(StrEnum):
    """The kind of link a terminal serves."""

    INTRA_ORBIT = "intra_orbit"
    INTER_ORBIT = "inter_orbit"
    GROUND = "ground"


def _require_positive(value: float, what: str) -> None:
    if not (math.isfinite(value) and value > 0):
        raise DomainError(f"{what}: deve essere finito e > 0, invece è {value}")


@dataclass(frozen=True, slots=True)
class PlmmModule:
    """The PLMM: the memory that holds the data of the requests.

    Attributes:
        capacity_gb: Capacity available to the requests, in Gb.
    """

    capacity_gb: float

    def __post_init__(self) -> None:
        _require_positive(self.capacity_gb, "capacità della PLMM")


@dataclass(frozen=True, slots=True)
class HpcModule:
    """The HPC: the computer of the satellite, and the router that feeds it.

    Attributes:
        rate_gbps: Rate of the HPC-router link, the same in both directions, in Gbps.
        windows: Computing windows, net of the container start-up.
    """

    rate_gbps: float
    windows: WindowSet

    def __post_init__(self) -> None:
        _require_positive(self.rate_gbps, "velocità dell'HPC")

    def io_time(self, size_gb: float) -> float:
        """Seconds needed to read ``size_gb`` from the PLMM, or to write it there."""
        return size_gb / self.rate_gbps


@dataclass(frozen=True, slots=True)
class Terminal:
    """One terminal of the OCT: the kind of link it serves, and its rate.

    Attributes:
        kind: The kind of link.
        rate_gbps: Rate of the terminal, in Gbps.
    """

    kind: LinkKind
    rate_gbps: float

    def __post_init__(self) -> None:
        _require_positive(self.rate_gbps, f"terminale {self.kind}, velocità")


@dataclass(frozen=True, slots=True)
class OctModule:
    """The OCT: the terminals of the satellite. It has at least one."""

    terminals: tuple[Terminal, ...]

    def __post_init__(self) -> None:
        if not self.terminals:
            raise DomainError("il modulo OCT deve avere almeno un terminale")


@dataclass(frozen=True, slots=True)
class Satellite:
    """A satellite: its identifier, and its three modules.

    Attributes:
        id: Identifier, unique in the constellation. The instance is what identifies the satellite.
        plmm: The PLMM.
        hpc: The HPC.
        oct: The OCT.
    """

    id: str
    plmm: PlmmModule
    hpc: HpcModule
    oct: OctModule

    def __post_init__(self) -> None:
        if not self.id:
            raise DomainError("l'identificativo del satellite non può essere vuoto")
