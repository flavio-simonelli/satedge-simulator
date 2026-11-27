"""Candidate links: every link the network can make, between two terminals, with its availability.

A candidate link is a fact of the network: which terminals can talk, when they can, and how long
the signal takes. Which candidates are active at a given instant is a decision of the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from satedge_simulator.domain.availability import Availability
from satedge_simulator.domain.quantities import Duration, Rate, Time
from satedge_simulator.domain.terminal import Terminal
from satedge_simulator.errors import DomainError


class Latency(Protocol):
    """How long a signal takes over a link, at an instant. A constant one, or one computed from
    the positions of the satellites, is a new class with this method: nothing else has to change."""

    def at(self, t: Time) -> Duration: ...


@dataclass(frozen=True, slots=True)
class ConstantLatency:
    """The same latency at every instant.

    Attributes:
        value: Propagation latency, more than zero.
    """

    value: Duration

    def __post_init__(self) -> None:
        if self.value == Duration.ZERO:
            raise DomainError("the latency must be > 0")

    def at(self, t: Time) -> Duration:
        return self.value


@dataclass(frozen=True, slots=True)
class CandidateLink:
    """A link that the network can make between two terminals.

    Attributes:
        a: One terminal.
        b: The other terminal. It is a different terminal, of the same kind.
        latency: How long a signal takes over the link, as a function of the instant.
        availability: When the link can be used: when the two terminals see each other.
    """

    a: Terminal
    b: Terminal
    latency: Latency
    availability: Availability

    def __post_init__(self) -> None:
        if self.a is self.b:
            raise DomainError("a link joins two different terminals")
        if self.a.kind != self.b.kind:
            raise DomainError(
                f"a link joins terminals of one kind, got {self.a.kind} and {self.b.kind}"
            )

    def latency_at(self, t: Time) -> Duration:
        """The time a signal takes over the link at ``t``."""
        return self.latency.at(t)

    @property
    def capacity(self) -> Rate:
        """The slower of the two terminals: the rate the link can carry."""
        return min(self.a.rate, self.b.rate)
