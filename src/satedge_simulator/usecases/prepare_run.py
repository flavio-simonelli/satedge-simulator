"""Use case: get what a run needs, through the ports."""

from __future__ import annotations

from dataclasses import dataclass

from satedge_simulator.domain.network import Network
from satedge_simulator.ports.network import NetworkRepository
from satedge_simulator.ports.workload import WorkflowSource, WorkloadRepository


@dataclass(frozen=True, slots=True)
class PreparedRun:
    """What one run needs.

    Attributes:
        network: The network that is simulated.
        workload: The source of the requests. It serves this run only.
    """

    network: Network
    workload: WorkflowSource


def prepare_run(
    networks: NetworkRepository,
    workloads: WorkloadRepository,
    network_reference: str,
    workload_reference: str,
) -> PreparedRun:
    """Load a network, and the source of a workload that runs on it.

    Raises:
        InputError: If the network or the workload is not valid.
    """
    network = networks.load(network_reference)
    workload = workloads.load(workload_reference, network)
    return PreparedRun(network, workload)
