"""Bootstrap: the composition root. It chooses the adapters and gives them to the use cases.

It is the only place that knows both the core and the adapters it runs with, so it is where one
adapter is connected to another: here, what is read from the workload file to the source that
gives its requests.
"""

from __future__ import annotations

from pathlib import Path

from satedge_simulator.adapters.workload.explicit import ExplicitWorkflowSource
from satedge_simulator.domain.network import Network
from satedge_simulator.io.loading.network import FileNetworkRepository
from satedge_simulator.io.loading.workload import load_workload
from satedge_simulator.io.scenario import read_scenario
from satedge_simulator.io.workload import StochasticWorkloadDoc
from satedge_simulator.ports.workload import WorkflowSource
from satedge_simulator.usecases.prepare_run import PreparedRun, prepare_run


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


def prepare_run_from_files(scenario_file: str | Path) -> PreparedRun:
    """Prepare a run from a scenario file, which also names the workload file.

    Raises:
        DocumentError: If a file cannot be read or is not valid.
        NotImplementedError: For a stochastic workload, until its generator is written.
    """
    workload_file = read_scenario(scenario_file).workload
    return prepare_run(
        FileNetworkRepository(),
        FileWorkloadRepository(),
        str(scenario_file),
        str(workload_file),
    )
