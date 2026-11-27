"""Workload: the requests, each a pipeline of tasks that starts from raw data on a satellite."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from satedge_simulator.domain.quantities import DataSize, Duration, Time
from satedge_simulator.domain.satellite import Satellite
from satedge_simulator.errors import DomainError


class Priority(StrEnum):
    """Priority class of a request: urgent, or non urgent."""

    URGENT = "urgent"
    NON_URGENT = "non_urgent"


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """One task of a pipeline.

    Attributes:
        execution: Execution time on the HPC, more than zero, the same on every satellite.
            It excludes reading the input and writing the output.
        output_size: Size of the data the task produces, more than zero.
    """

    execution: Duration
    output_size: DataSize

    def __post_init__(self) -> None:
        if self.execution == Duration.ZERO:
            raise DomainError("the execution time of a task must be > 0")
        if self.output_size.gigabits == 0:
            raise DomainError("the output size of a task must be > 0")


@dataclass(frozen=True, slots=True, eq=False)
class RequestSpec:
    """A request: a pipeline whose final output must reach the ground station.

    A request is identified by its instance, not by its ``id``: two requests may share the same
    ``id``, and equality and hashing are those of the object itself.

    Attributes:
        id: Descriptive label, for people reading the results. It is not unique.
        priority: Priority class.
        origin: The satellite of the constellation that holds the raw data: this instance, not
            a copy of it.
        arrival: Instant the request reaches the ground segment.
        release: Instant the raw data becomes available on ``origin``. Not before ``arrival``.
        deadline: Instant by which the final output must reach the ground station. Not before
            ``release``.
        raw_size: Size of the raw data, more than zero.
        tasks: The pipeline, in execution order, with at least one task.
    """

    id: str
    priority: Priority
    origin: Satellite
    arrival: Time
    release: Time
    deadline: Time
    raw_size: DataSize
    tasks: tuple[TaskSpec, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.origin, Satellite):
            raise DomainError("the origin of a request must be a satellite")
        if not self.id:
            raise DomainError("the request identifier must not be empty")
        if not self.tasks:
            raise DomainError(
                f"request {self.id}: the pipeline must have at least one task"
            )
        if self.release < self.arrival:
            raise DomainError(
                f"request {self.id}: the release {self.release.seconds} is before the "
                f"arrival {self.arrival.seconds}"
            )
        if self.deadline < self.release:
            raise DomainError(
                f"request {self.id}: the deadline {self.deadline.seconds} is before the "
                f"release {self.release.seconds}"
            )
        if self.raw_size.gigabits == 0:
            raise DomainError(f"request {self.id}: the raw data size must be > 0")

    @property
    def output_size(self) -> DataSize:
        """Size of the final output."""
        return self.tasks[-1].output_size
