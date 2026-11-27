"""Ground station: the node that receives the final outputs of the requests and never relays data.

It has antennas, and each antenna carries one link at a time: they limit how many links the
station can serve at once.
"""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.domain.terminal import LinkKind, Terminal
from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True, eq=False)
class GroundStation:
    """The ground station: its identifier, and its antennas. It has at least one antenna.

    Attributes:
        id: Identifier, unique in the constellation. The instance is what identifies the station.
        antennas: The antennas, each a terminal of kind ground, listed once, in any order.
    """

    id: str
    antennas: tuple[Terminal, ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise DomainError("the ground station identifier must not be empty")
        if not self.antennas:
            raise DomainError(
                f"ground station {self.id}: it must have at least one antenna"
            )
        if len(set(self.antennas)) != len(self.antennas):
            raise DomainError(
                f"ground station {self.id}: it lists the same antenna twice"
            )
        for antenna in self.antennas:
            if antenna.kind is not LinkKind.GROUND:
                raise DomainError(
                    f"ground station {self.id}: every antenna must be of kind "
                    f"{LinkKind.GROUND}, got {antenna.kind}"
                )
