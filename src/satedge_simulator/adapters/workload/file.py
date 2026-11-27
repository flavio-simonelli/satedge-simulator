"""Workload files: the repository of the workloads described by the input files."""

from __future__ import annotations

from satedge_simulator.adapters.workload.explicit import ExplicitWorkflowSource
from satedge_simulator.domain.network import Network
from satedge_simulator.io.loading.workload import load_workload
from satedge_simulator.io.workload import StochasticWorkloadDoc
from satedge_simulator.ports.workload import WorkflowSource


class FileWorkloadRepository:
    """The :class:`~satedge_simulator.ports.workload.WorkloadRepository` of the workload files.

    A reference is the path of a workload file.
    """

    def load(self, reference: str, network: Network) -> WorkflowSource:
        """Read the workload file ``reference``, and create the source of its requests.

        Raises:
            DocumentError: If the file cannot be read or is not valid, or a request is not
                valid for the network. The message names the file.
            NotImplementedError: For a stochastic workload, until its generator is written.
        """
        workload = load_workload(reference, network)
        if isinstance(workload, StochasticWorkloadDoc):
            raise NotImplementedError(
                f"{reference}: the generator of a stochastic workload is not written yet"
            )
        return ExplicitWorkflowSource(workload, network)
