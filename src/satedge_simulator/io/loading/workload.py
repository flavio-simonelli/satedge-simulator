"""Workload loading: the workload file, read and translated.

An explicit workload is translated into requests of the domain. A stochastic one has no requests
to translate, only the parameters of its model: its document is returned as it is. What gives the
requests to the simulation is not decided here.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from satedge_simulator.domain.network import Network
from satedge_simulator.domain.quantities import DataSize, Duration, Time
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.satellite import Satellite
from satedge_simulator.errors import DocumentError
from satedge_simulator.io.loading.conventions import DEFAULT_DEADLINE_AFTER_RELEASE
from satedge_simulator.io.loading.errors import errors_in
from satedge_simulator.io.workload import (
    ExplicitWorkloadDoc,
    RequestDoc,
    StochasticWorkloadDoc,
    WorkloadFile,
)


def load_workload(
    path: str | Path, network: Network
) -> tuple[RequestSpec, ...] | StochasticWorkloadDoc:
    """Read the workload file ``path``, to run on ``network``.

    Returns:
        The requests of an explicit workload, in the order the file lists them, or the document
        of a stochastic one.

    Raises:
        DocumentError: If the file cannot be read or is not valid, or a request is not valid
            for the network. The message names the file.
    """
    document = WorkloadFile.read(path)
    if isinstance(document, StochasticWorkloadDoc):
        return document
    if isinstance(document, ExplicitWorkloadDoc):
        satellites = {s.id: s for s in network.satellites}
        return build_requests(document, satellites, Path(path))
    # A kind registered in the files, with no translation here.
    raise NotImplementedError(f"{path}: {type(document).__name__} is not translated")


def build_requests(
    workload: ExplicitWorkloadDoc,
    satellites: Mapping[str, Satellite],
    workload_file: Path,
) -> tuple[RequestSpec, ...]:
    """The requests of ``workload``, in the order the file lists them.

    Without ``arrival_s`` a request arrives at its release, and without ``deadline_s`` it has
    the default delay of its priority class after the release. The path is used by the error
    messages only.

    Raises:
        DocumentError: If an origin is not in ``satellites``, or a value breaks a rule of the
            domain. The message names the file and the request.
    """
    requests: list[RequestSpec] = []
    for doc in workload.requests:
        if doc.origin not in satellites:
            raise DocumentError(
                f"{workload_file}: request {doc.id!r}: {doc.origin!r} is not a satellite "
                "of the network"
            )
        with errors_in(workload_file, f"request {doc.id!r}"):
            requests.append(_request(doc, satellites[doc.origin]))
    return tuple(requests)


def _request(doc: RequestDoc, origin: Satellite) -> RequestSpec:
    priority = Priority(doc.priority.value)
    release = Time(doc.release_s)
    arrival = release if doc.arrival_s is None else Time(doc.arrival_s)
    if doc.deadline_s is None:
        deadline = release + DEFAULT_DEADLINE_AFTER_RELEASE[priority]
    else:
        deadline = Time(doc.deadline_s)
    return RequestSpec(
        id=doc.id,
        priority=priority,
        origin=origin,
        arrival=arrival,
        release=release,
        deadline=deadline,
        raw_size=DataSize(doc.raw_size_gb),
        tasks=tuple(
            TaskSpec(Duration(t.execution_s), DataSize(t.output_size_gb))
            for t in doc.tasks
        ),
    )
