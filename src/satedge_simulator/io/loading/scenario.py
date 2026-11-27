"""Scenario mapping: the documents of a scenario, turned into the scenario of the domain.

The files are read by :mod:`satedge_simulator.io.scenario`. This module builds the objects of the
domain from them. The scheduler file does not take part: it configures the planner.
"""

from __future__ import annotations

from pathlib import Path

from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.io.loading.errors import errors_in
from satedge_simulator.io.loading.topology import build_network
from satedge_simulator.io.loading.workload import build_requests
from satedge_simulator.io.scenario import ScenarioFiles, read_scenario
from satedge_simulator.io.workload import ExplicitWorkloadDoc


def build_scenario(path: str | Path, files: ScenarioFiles) -> Scenario:
    """The scenario that ``files`` describe.

    An explicit workload gives the requests of the scenario. With a stochastic one the scenario
    has no requests: whoever calls this builds their generator from ``files.workload``.

    Args:
        path: The scenario file that ``files`` were read from, to name the files in the errors.
        files: The documents, as :func:`~satedge_simulator.io.scenario.read_scenario` returns
            them.

    Raises:
        DocumentError: If a value breaks a rule of the domain, or a link names an unknown node.
            The message names the file that holds the value.
    """
    base = Path(path).parent
    workload_file = base / files.scenario.workload
    network = build_network(
        files.topology,
        files.satellites,
        topology_file=base / files.scenario.topology,
        satellites_file=base / files.scenario.satellites,
    )
    requests = ()
    if isinstance(files.workload, ExplicitWorkloadDoc):
        satellites = {s.id: s for s in network.satellites}
        requests = build_requests(files.workload, satellites, workload_file)
    with errors_in(workload_file, "requests"):
        return Scenario(network, requests)


def load_scenario(path: str | Path) -> Scenario:
    """Read the scenario in ``path``, and build it: see :func:`build_scenario`.

    Raises:
        DocumentError: If a file cannot be read or is not valid, the files do not agree with
            each other, or a value breaks a rule of the domain. The message names a file.
    """
    return build_scenario(path, read_scenario(path))
