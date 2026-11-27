"""Ports of the workload: the contracts between the core and whatever gives the requests.

The simulation takes the requests one at a time, while it runs, and a generator creates each one
only then. The simulation does not know whether the requests were written in advance or are
generated: a :class:`WorkloadRepository` gives it the source.

The workload is open loop: what is requested, and when, does not depend on how the simulation
goes. So a source receives nothing from the simulation while it runs. A workload that reacts to
the simulation would need another port.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from satedge_simulator.domain.network import Network
from satedge_simulator.domain.requests import RequestSpec


class WorkflowSource(Protocol):
    """The requests of one run, in the order they arrive."""

    def requests(self) -> Iterator[RequestSpec]:
        """The requests, ordered by ``arrival``.

        Every implementation guarantees that:

        - a request is produced only when the iterator is asked for it: calling this method
          produces none, and asking for one never creates the following ones. A generator
          creates one request for each request taken;
        - the arrivals never decrease. Requests with the same arrival come in their FIFO order;
        - each request is a different instance, and it comes once;
        - each request can run on the network the source was created for: see
          :meth:`~satedge_simulator.domain.network.Network.require_request`;
        - the requests depend only on what the source was created with, including the seed of
          a generator: sources created in the same way give requests with the same values, in
          the same order.

        The iterator may never end: the caller decides when to stop taking requests, so a source
        does not need to know when the run ends.

        A source serves one run: this method is called once. Another run needs another source.
        """
        ...


class WorkloadRepository(Protocol):
    """Where the workloads are kept."""

    def load(self, reference: str, network: Network) -> WorkflowSource:
        """A new source of the requests of the workload that ``reference`` names, to run on
        ``network``. The origins of its requests are satellites of that very network.

        What a reference is, such as the path of a file, is decided by the implementation.

        Raises:
            InputError: If there is no such workload, or it is not valid for the network.
        """
        ...
