"""Terminal: one end of a link. An OCT terminal of a satellite, or an antenna of the ground station.

A terminal carries one link at a time. Each terminal is its own object: two terminals with the same
kind and rate are still two different terminals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from satedge_simulator.domain.quantities import Rate


class LinkKind(StrEnum):
    """The kind of link a terminal serves."""

    INTRA_ORBIT = "intra_orbit"
    INTER_ORBIT = "inter_orbit"
    GROUND = "ground"


@dataclass(frozen=True, slots=True, eq=False)
class Terminal:
    """A terminal: the kind of link it serves, and its rate. Identity is the instance.

    Attributes:
        kind: The kind of link.
        rate: Rate of the terminal.
    """

    kind: LinkKind
    rate: Rate
