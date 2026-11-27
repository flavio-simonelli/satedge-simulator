"""Workload loading: the workload file, turned into the requests or the model of the domain.

The file is read by :mod:`satedge_simulator.io.workload`, which knows nothing of the domain. This
module turns the document into the objects of the domain.
"""

from __future__ import annotations

from pathlib import Path

from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.topology import Constellation
from satedge_simulator.domain.workload_model import WorkloadModel
from satedge_simulator.errors import DocumentError, DomainError
from satedge_simulator.io.workload import (
    RequestDoc,
    StochasticWorkloadDoc,
    WorkloadFile,
)
from satedge_simulator.loading.conventions import DEFAULT_DEADLINE_AFTER_RELEASE_S


def load_workload(
    path: str | Path, constellation: Constellation
) -> tuple[RequestSpec, ...] | WorkloadModel:
    """Read the workload in ``path``.

    An explicit workload gives its requests, with the default deadlines of their priority
    classes.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema, or if two
            requests share an identifier. The message names the file.
        NotImplementedError: For a stochastic workload, for now: its tasks are not yet in the
            domain model.
    """
    document = WorkloadFile.read(path)
    if isinstance(document, StochasticWorkloadDoc):
        raise NotImplementedError(
            "a stochastic workload is not connected to the domain model yet"
        )
    try:
        requests = tuple(_request(doc, constellation) for doc in document.requests)
    except DomainError as error:
        raise DocumentError(f"{path}: {error}") from error
    return requests


def _request(doc: RequestDoc, constellation: Constellation) -> RequestSpec:
    priority = Priority[doc.priority.name]
    deadline = doc.deadline_s
    if deadline is None:
        deadline = doc.release_s + DEFAULT_DEADLINE_AFTER_RELEASE_S[priority]
    try:
        return RequestSpec(
            id=doc.id,
            priority=priority,
            origin=constellation.satellite(doc.origin),
            arrival_s=doc.release_s if doc.arrival_s is None else doc.arrival_s,
            release_s=doc.release_s,
            deadline_s=deadline,
            raw_size_gb=doc.raw_size_gb,
            tasks=tuple(TaskSpec(t.execution_s, t.output_size_gb) for t in doc.tasks),
        )
    except DomainError as error:
        raise DocumentError(f"request {doc.id}: {error}") from error
