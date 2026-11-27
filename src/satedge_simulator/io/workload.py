"""Workload file: explicit requests, or the parameters of a stochastic workload.

The ``kind`` field says which one the file holds. ``explicit`` lists each request, each a
pipeline of tasks that starts from raw data on a satellite. ``stochastic`` gives the parameters
of the model that generates the requests during the simulation.

This module only reads the file. The conversion into the objects of the domain is in
:mod:`satedge_simulator.loading.workload`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, ClassVar, Literal

from pydantic import AfterValidator, Field, RootModel

from satedge_simulator.io.base import Document, VersionedDocument, read_document


class WorkloadKind(StrEnum):
    """How the workload is given: as requests, or as a stochastic model."""

    EXPLICIT = "explicit"
    STOCHASTIC = "stochastic"


class PriorityName(StrEnum):
    """The priority classes as the workload file spells them."""

    URGENT = "urgent"
    NON_URGENT = "non_urgent"


class TaskDoc(Document):
    """One task of an explicit request."""

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


class ExplicitWorkloadDoc(VersionedDocument):
    """A workload of explicit requests, in FIFO order within each priority class."""

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    kind: Literal[WorkloadKind.EXPLICIT]
    requests: list[RequestDoc] = Field(default_factory=list)


def _check_float_range(value: tuple[float, float]) -> tuple[float, float]:
    low, high = value
    if low < 0 or low > high:
        raise ValueError("a range [low, high] needs 0 <= low <= high")
    return value


def _check_task_count_range(value: tuple[int, int]) -> tuple[int, int]:
    low, high = value
    if low < 1 or low > high:
        raise ValueError("a range of tasks [low, high] needs 1 <= low <= high")
    return value


FloatRange = Annotated[tuple[float, float], AfterValidator(_check_float_range)]
"""A range ``[low, high]``: each value is drawn uniformly between the two."""

TaskCountRange = Annotated[tuple[int, int], AfterValidator(_check_task_count_range)]
"""A range ``[low, high]`` of whole numbers of tasks."""


class LogNormalDoc(Document):
    """A positive, skewed quantity, described by its mean and its coefficient of variation.

    ``cv`` is the standard deviation divided by the mean: 0.5 means a moderate spread, 2 a
    very long tail. Each draw is independent.
    """

    mean: float = Field(gt=0)
    cv: float = Field(gt=0)


class TaskModelDoc(Document):
    """What every task of a stochastic request is like. Each task draws its values here."""

    execution_s: LogNormalDoc
    output_size_gb: LogNormalDoc


class StochasticWorkloadDoc(VersionedDocument):
    """A stochastic workload: the model that generates the requests during the simulation.

    Each request has a raw data of ``raw_size_gb``, and a number of tasks drawn from
    ``tasks_per_request``. Every task draws its execution time and its output size from ``task``.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    kind: Literal[WorkloadKind.STOCHASTIC]
    arrivals_per_hour: float = Field(gt=0)
    urgent_probability: float = Field(ge=0, le=1)
    raw_size_gb: FloatRange
    tasks_per_request: TaskCountRange
    task: TaskModelDoc


class WorkloadDoc(
    RootModel[
        Annotated[
            ExplicitWorkloadDoc | StochasticWorkloadDoc, Field(discriminator="kind")
        ]
    ]
):
    """A workload file: explicit requests, or a stochastic model, chosen by ``kind``."""


def read_workload(path: str | Path) -> ExplicitWorkloadDoc | StochasticWorkloadDoc:
    """Read and validate the workload file in ``path``.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema. The message
            names the file.
    """
    return read_document(path, WorkloadDoc).root
