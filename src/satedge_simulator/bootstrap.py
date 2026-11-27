"""Bootstrap: the composition root. It chooses the adapters and gives them to the use cases.

It is the only place that knows both the use cases and the adapters they run with.
"""

from __future__ import annotations

from pathlib import Path

from satedge_simulator.adapters.network.file import FileNetworkRepository
from satedge_simulator.adapters.workload.file import FileWorkloadRepository
from satedge_simulator.application.prepare_run import PreparedRun, prepare_run
from satedge_simulator.io.scenario import read_scenario


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
