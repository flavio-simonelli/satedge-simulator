"""Port of the network: the contract between the core and wherever the networks are kept."""

from __future__ import annotations

from typing import Protocol

from satedge_simulator.domain.network import Network


class NetworkRepository(Protocol):
    """Where the networks are kept."""

    def load(self, reference: str) -> Network:
        """The network that ``reference`` names. What a reference is, such as the path of a
        file, is decided by the implementation.

        Raises:
            InputError: If there is no such network, or it is not valid.
        """
        ...
