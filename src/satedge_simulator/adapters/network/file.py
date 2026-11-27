"""Network files: the repository of the networks described by the input files."""

from __future__ import annotations

from satedge_simulator.domain.network import Network
from satedge_simulator.io.loading.network import load_network


class FileNetworkRepository:
    """The :class:`~satedge_simulator.ports.network.NetworkRepository` of the input files.

    A reference is the path of a scenario file, which names the topology and satellites files.
    """

    def load(self, reference: str) -> Network:
        """The network of the scenario file ``reference``.

        Raises:
            DocumentError: If a file cannot be read or is not valid, or does not describe a
                valid network: see :func:`~satedge_simulator.io.loading.network.load_network`.
        """
        return load_network(reference)
