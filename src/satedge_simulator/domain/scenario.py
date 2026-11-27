"""Scenario: the network and the requests it serves, checked together."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from satedge_simulator.domain.network import Network
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True, eq=False)
class Scenario:
    """What a simulation runs: the network, and the requests known before it starts.

    Requests generated during the run are not listed here: their source checks each one
    with :meth:`require_request`, so every request obeys the same rules, whatever its origin.

    Attributes:
        network: The network.
        requests: The requests known in advance, each listed once. Empty when the workload is
            generated during the run.

    Raises:
        DomainError: If a request starts from a satellite that is not in the network, or the
            same request is listed twice.
    """

    network: Network
    requests: tuple[RequestSpec, ...] = ()

    def __post_init__(self) -> None:
        # Accept any iterable, and store a tuple so the scenario stays immutable.
        object.__setattr__(self, "requests", tuple(self.requests))
        seen: set[RequestSpec] = set()
        for request in self.requests:
            if request in seen:
                raise DomainError(f"request {request.id!r} is listed twice")
            seen.add(request)
            self.require_request(request)

    def require_request(self, request: RequestSpec) -> None:
        """Check that ``request`` can run in this scenario.

        Raises:
            DomainError: If its origin is not a satellite of the network.
        """
        if not self.network.has(request.origin):
            raise DomainError(
                f"request {request.id!r} starts from satellite {request.origin.id!r}, "
                "which is not in the network"
            )

    def with_requests(self, requests: Iterable[RequestSpec]) -> Scenario:
        """A new scenario with the same network and ``requests``, checked again."""
        return Scenario(self.network, tuple(requests))
