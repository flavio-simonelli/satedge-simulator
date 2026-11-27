"""Explicit workload: the source of requests that are all known in advance."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from satedge_simulator.domain.network import Network
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.errors import DomainError, StateError


class ExplicitWorkflowSource:
    """The :class:`~satedge_simulator.ports.workload.WorkflowSource` of a list of requests.

    The requests may be listed in any order: they are given in order of arrival, and those with
    the same arrival in the order of the list.

    Args:
        requests: The requests, each listed once.
        network: The network they run on.

    Raises:
        DomainError: If a request starts from a satellite that is not in the network, or the
            same request is listed twice.
    """

    def __init__(self, requests: Iterable[RequestSpec], network: Network) -> None:
        listed = tuple(requests)
        seen: set[RequestSpec] = set()
        for request in listed:
            if request in seen:
                raise DomainError(f"request {request.id!r} is listed twice")
            seen.add(request)
            network.require_request(request)
        # The sort is stable: it keeps the order of the list among equal arrivals.
        self._requests = tuple(sorted(listed, key=lambda r: r.arrival))
        self._taken = False

    def requests(self) -> Iterator[RequestSpec]:
        """The requests, in order of arrival.

        Raises:
            StateError: If called a second time: a source serves one run.
        """
        if self._taken:
            raise StateError(
                "a workflow source serves one run: its requests were taken"
            )
        self._taken = True
        return iter(self._requests)
