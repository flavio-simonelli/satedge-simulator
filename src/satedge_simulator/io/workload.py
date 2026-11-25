"""Workload file: the requests, each a pipeline of tasks that starts from raw data on a satellite."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator

from satedge_simulator.domain.workload import (
    DEFAULT_DEADLINE_AFTER_RELEASE_S,
    Priority,
    RequestSpec,
    TaskSpec,
)
from satedge_simulator.errors import DocumentError, ScenarioError
from satedge_simulator.io.base import Document, check_schema_version, read_document


class PriorityName(StrEnum):
    """The priority classes as the workload file spells them."""

    URGENT = "urgent"
    NON_URGENT = "non_urgent"


class TaskDoc(Document):
    """One task of a pipeline."""

    execution_s: float
    output_size_gb: float


class RequestDoc(Document):
    """One request.

    Without ``deadline_s`` the deadline is ``release_s`` plus the delay of its priority class.
    Without ``arrival_s`` the request arrives when its raw data is released.
    """

    id: str
    priority: PriorityName
    origin: str
    release_s: float
    arrival_s: float | None = None
    deadline_s: float | None = None
    raw_size_gb: float
    tasks: list[TaskDoc] = Field(min_length=1)


class WorkloadDoc(Document):
    """A workload file: the requests, in FIFO order within each priority class."""

    schema_version: str
    requests: list[RequestDoc] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


def load_workload(path: str | Path) -> tuple[RequestSpec, ...]:
    """Read the requests in ``path``, with the default deadlines of their priority classes.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema, if two requests
            share an identifier, or if a request is not valid. The message names the file.
    """
    document = read_document(path, WorkloadDoc)
    requests = tuple(_request(doc) for doc in document.requests)
    ids = [r.id for r in requests]
    if len(set(ids)) != len(ids):
        raise DocumentError(f"{path}: identificativi di richiesta duplicati")
    return requests


def _request(doc: RequestDoc) -> RequestSpec:
    priority = Priority[doc.priority.name]
    deadline = doc.deadline_s
    if deadline is None:
        deadline = doc.release_s + DEFAULT_DEADLINE_AFTER_RELEASE_S[priority]
    try:
        return RequestSpec(
            id=doc.id,
            priority=priority,
            origin=doc.origin,
            arrival_s=doc.release_s if doc.arrival_s is None else doc.arrival_s,
            release_s=doc.release_s,
            deadline_s=deadline,
            raw_size_gb=doc.raw_size_gb,
            tasks=tuple(TaskSpec(t.execution_s, t.output_size_gb) for t in doc.tasks),
        )
    except ScenarioError as error:
        raise DocumentError(f"richiesta {doc.id}: {error}") from error
