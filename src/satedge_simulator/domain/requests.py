"""Workload: the requests, each a pipeline of tasks that starts from raw data on a satellite."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from satedge_simulator.domain.topology import Satellite
from satedge_simulator.errors import DomainError


class Priority(StrEnum):
    """Priority class of a request: urgent, or non urgent."""

    URGENT = "urgent"
    NON_URGENT = "non_urgent"


def _require_finite_and_greater(
    value: float, minimum: float, what: str, *, strict: bool = False
) -> None:
    """Check that ``value`` is finite and not below ``minimum``, or above it if ``strict``."""
    ok = value > minimum if strict else value >= minimum
    if not (math.isfinite(value) and ok):
        bound = "> " if strict else ">= "
        raise DomainError(f"{what}: must be finite and {bound}{minimum}, got {value}")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """One task of a pipeline.

    Attributes:
        execution_s: Execution time on the HPC, in seconds, the same on every satellite.
            It excludes reading the input and writing the output.
        output_size_gb: Size of the data the task produces, in Gb.
    """

    execution_s: float
    output_size_gb: float

    def __post_init__(self) -> None:
        _require_finite_and_greater(
            self.execution_s, 0.0, "the execution time of the task", strict=True
        )
        _require_finite_and_greater(
            self.output_size_gb, 0.0, "the output size of the task", strict=True
        )


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
        arrival_s: Instant the request reaches the ground segment, in seconds.
        release_s: Instant the raw data becomes available on ``origin``, in seconds. Not before
            ``arrival_s``.
        deadline_s: Absolute instant by which the final output must reach the ground station.
            Not before ``release_s``.
        raw_size_gb: Size of the raw data, in Gb.
        tasks: The pipeline, in execution order.
    """

    id: str
    priority: Priority
    origin: Satellite
    arrival_s: float
    release_s: float
    deadline_s: float
    raw_size_gb: float
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
        _require_finite_and_greater(self.arrival_s, 0.0, f"request {self.id}, arrival")
        _require_finite_and_greater(
            self.release_s, self.arrival_s, f"request {self.id}, release"
        )
        _require_finite_and_greater(
            self.deadline_s, self.release_s, f"request {self.id}, deadline"
        )
        _require_finite_and_greater(
            self.raw_size_gb, 0.0, f"request {self.id}, raw data size", strict=True
        )

    @property
    def output_size_gb(self) -> float:
        """Size of the final output, in Gb."""
        return self.tasks[-1].output_size_gb

    def data_sizes_gb(self) -> tuple[float, ...]:
        """Sizes of the data items: the raw data, then the output of each task."""
        return (self.raw_size_gb, *(task.output_size_gb for task in self.tasks))

    def hpc_occupancy_s(self, task_index: int, hpc_rate_gbps: float) -> float:
        """Seconds the HPC is busy with task ``task_index``.

        It is the time to read the input from the PLMM, plus the execution, plus the time to
        write the output into the PLMM. The occupancy is what the computing window must hold.
        """
        task = self.tasks[task_index]
        input_gb = self.data_sizes_gb()[task_index]
        return (
            input_gb / hpc_rate_gbps
            + task.execution_s
            + task.output_size_gb / hpc_rate_gbps
        )
