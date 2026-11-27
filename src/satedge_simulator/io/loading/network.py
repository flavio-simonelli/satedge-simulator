"""Network loading: the network of a scenario file, read and translated.

Only the scenario, satellites and topology files are read: the network does not depend on the
workload nor on the scheduler. The network is built by
:mod:`satedge_simulator.io.loading.topology`.
"""

from __future__ import annotations

from pathlib import Path

from satedge_simulator.domain.network import Network
from satedge_simulator.io.loading.topology import build_network
from satedge_simulator.io.satellites import load_satellites
from satedge_simulator.io.scenario import read_scenario
from satedge_simulator.io.topology import read_topology


def load_network(path: str | Path) -> Network:
    """Read the scenario file ``path`` and its satellites and topology files, and build the
    network.

    Raises:
        DocumentError: If one of the three files cannot be read or is not valid, the topology
            uses a name that is not defined, or a value breaks a rule of the domain. The
            message names a file.
    """
    paths = read_scenario(path)
    satellite_types = load_satellites(paths.satellites)
    return build_network(
        read_topology(paths.topology),
        satellite_types,
        topology_file=paths.topology,
        satellites_file=paths.satellites,
    )
