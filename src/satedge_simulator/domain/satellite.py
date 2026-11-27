"""Satellite: the node that computes, stores data and relays it, made of three modules.

- the HPC computes on the data, when it is available;
- the PLMM stores the data of the requests, up to its capacity;
- the OCT is the set of terminals that link the satellite to the other nodes.
"""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.domain.availability import Availability
from satedge_simulator.domain.quantities import DataSize, Duration, Rate
from satedge_simulator.domain.terminal import Terminal
from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True)
class PlmmModule:
    """The PLMM: the memory that holds the data of the requests.

    Attributes:
        capacity: Capacity available to the requests, more than zero.
    """

    capacity: DataSize

    def __post_init__(self) -> None:
        if self.capacity.gigabits == 0:
            raise DomainError("the PLMM capacity must be > 0")


@dataclass(frozen=True, slots=True)
class HpcModule:
    """The HPC: the computer of the satellite, its memory, the router that feeds it, and when
    it is on.

    Attributes:
        rate: Rate of the HPC-router link, the same in both directions.
        memory: Memory of the HPC, more than zero.
        availability: When the HPC can compute, net of the start-up of its containers.
    """

    rate: Rate
    memory: DataSize
    availability: Availability

    def __post_init__(self) -> None:
        if self.memory.gigabits == 0:
            raise DomainError("the HPC memory must be > 0")

    def io_time(self, size: DataSize) -> Duration:
        """The time needed to read ``size`` from the PLMM, or to write it there."""
        return self.rate.transfer_time(size)


@dataclass(frozen=True, slots=True)
class OctModule:
    """The OCT: the terminals of the satellite. It has at least one."""

    terminals: tuple[Terminal, ...]

    def __post_init__(self) -> None:
        if not self.terminals:
            raise DomainError("the OCT module must have at least one terminal")
        if len(set(self.terminals)) != len(self.terminals):
            raise DomainError("the OCT module lists the same terminal twice")


@dataclass(frozen=True, slots=True, eq=False)
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
            raise DomainError("the satellite identifier must not be empty")
