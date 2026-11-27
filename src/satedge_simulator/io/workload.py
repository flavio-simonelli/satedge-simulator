"""Workload file: explicit requests, or the parameters of a stochastic workload.

The ``kind`` field says which variant of the file it is. ``explicit`` lists each request, and
``stochastic`` gives the parameters of a model that generates them. The values of the numbers,
including the order of the bounds of a range, are not checked here.

This module only reads the file. The conversion into the objects of the domain is in
:mod:`satedge_simulator.io.loading.workload`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field

from satedge_simulator.io.base import (
    Document,
    Registry,
    VersionedDocument,
    read_variant,
)


class WorkloadKind(StrEnum):
    """How the workload is given: as requests, or as a stochastic model."""

    EXPLICIT = "explicit"
    STOCHASTIC = "stochastic"


class PriorityName(StrEnum):
    """The priority classes as the workload file spells them."""

    URGENT = "urgent"
    NON_URGENT = "non_urgent"


class TaskDoc(Document):
    """One task of an explicit request.

    Attributes:
        execution_s: Execution time of the task, in seconds.
        output_size_gb: Size of the output of the task.
    """

    execution_s: float
    output_size_gb: float


class RequestDoc(Document):
    """One explicit request. The optional fields are filled in by
    :mod:`satedge_simulator.io.loading.workload`.

    Attributes:
        id: Label of the request.
        priority: Priority class.
        origin: Name of the satellite that holds the raw data.
        release_s: Instant the raw data is released, in seconds.
        arrival_s: Instant the request arrives, in seconds. It may be left out.
        deadline_s: Deadline of the request, in seconds. It may be left out.
        raw_size_gb: Size of the raw data.
        tasks: The tasks, in the order the file lists them.
    """

    id: str
    priority: PriorityName
    origin: str
    release_s: float
    arrival_s: float | None = None
    deadline_s: float | None = None
    raw_size_gb: float
    tasks: list[TaskDoc]


class WorkloadDoc(VersionedDocument):
    """The fields that a workload file has with every kind.

    Each kind is a subclass, registered in :data:`WORKLOADS` under its kind name.

    Attributes:
        schema_version: Version of the format of the file.
    """


WORKLOADS: Registry[WorkloadDoc] = Registry("kind")


@WORKLOADS.variant("explicit")
class ExplicitWorkloadDoc(WorkloadDoc):
    """A workload file that lists its requests.

    Attributes:
        kind: Always ``explicit``.
        requests: The requests. It may be left out: there are then no requests.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    kind: Literal[WorkloadKind.EXPLICIT]
    requests: list[RequestDoc] = Field(default_factory=list)


FloatRange = tuple[float, float]
"""A range, written as ``[low, high]``."""

TaskCountRange = tuple[int, int]
"""A range of numbers of tasks, written as ``[low, high]``."""


class LogNormalDoc(Document):
    """The parameters of a log-normal quantity.

    Attributes:
        mean: Mean of the quantity.
        cv: Coefficient of variation: the standard deviation divided by the mean.
    """

    mean: float
    cv: float


class TaskModelDoc(Document):
    """The parameters of the tasks of a stochastic workload.

    Attributes:
        execution_s: Execution time of a task, in seconds.
        output_size_gb: Size of the output of a task.
    """

    execution_s: LogNormalDoc
    output_size_gb: LogNormalDoc


@WORKLOADS.variant("stochastic")
class StochasticWorkloadDoc(WorkloadDoc):
    """A workload file with the parameters of a stochastic model.

    Attributes:
        kind: Always ``stochastic``.
        arrivals_per_hour: Rate of arrival of the requests, per hour.
        urgent_probability: Probability that a request is urgent.
        raw_size_gb: Range of the size of the raw data.
        tasks_per_request: Range of the number of tasks of a request.
        task: Parameters of the tasks.
        deadline_after_release_s: Delay of the deadline after the release, in seconds, by
            priority class. It may be left out.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    kind: Literal[WorkloadKind.STOCHASTIC]
    arrivals_per_hour: float
    urgent_probability: float
    raw_size_gb: FloatRange
    tasks_per_request: TaskCountRange
    task: TaskModelDoc
    deadline_after_release_s: dict[PriorityName, float] | None = None


class WorkloadFile:
    """The workload file: the reader of the variants registered in :data:`WORKLOADS`."""

    @classmethod
    def read(cls, path: str | Path) -> WorkloadDoc:
        """Read the workload file in ``path``, with the schema of the kind it names.

        Raises:
            DocumentError: If the format is unknown, the file cannot be read or its text is not
                valid in its format, it names no known kind, it does not match the schema of its
                kind, or its version is not supported. The message names the file.
        """
        return read_variant(path, WORKLOADS)
