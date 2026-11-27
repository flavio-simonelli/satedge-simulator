"""Orbit plane: the satellites that share one orbit."""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.domain.satellite import Satellite
from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True, eq=False)
class OrbitPlane:
    """An orbit, with the satellites on it.

    Attributes:
        name: Identifier of the plane, unique in the constellation.
        satellites: The satellites of the plane. Their identifiers are unique within the plane.
    """

    name: str
    satellites: tuple[Satellite, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise DomainError("the plane name must not be empty")
        if not self.satellites:
            raise DomainError(f"plane {self.name}: it must have at least one satellite")
        ids = [s.id for s in self.satellites]
        if len(set(ids)) != len(ids):
            raise DomainError(
                f"plane {self.name}: a satellite identifier is used twice"
            )
