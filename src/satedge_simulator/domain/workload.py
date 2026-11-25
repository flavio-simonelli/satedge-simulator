"""Workload: the requests, each a pipeline of tasks that starts from raw data on a satellite."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import ScenarioError


class Priority(StrEnum):
    """Priority class of a request: urgent, or non urgent."""

    URGENT = "urgent"
    NON_URGENT = "non_urgent"


def _require_finite_at_least(value: float, minimum: float, what: str) -> None:
    if not (math.isfinite(value) and value >= minimum):
        raise ScenarioError(
            f"{what}: deve essere finito e >= {minimum}, invece è {value}"
        )


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
        if not (math.isfinite(self.execution_s) and self.execution_s > 0):
            raise ScenarioError(
                f"il tempo di esecuzione del task deve essere finito e > 0, invece è {self.execution_s}"
            )
        if not (math.isfinite(self.output_size_gb) and self.output_size_gb > 0):
            raise ScenarioError(
                f"la dimensione dell'output del task deve essere finita e > 0, invece è {self.output_size_gb}"
            )


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """A request: a pipeline whose final output must reach the ground station.

    Attributes:
        id: Unique identifier.
        priority: Priority class.
        origin: Satellite that holds the raw data.
        arrival_s: Instant the request reaches the ground segment, in seconds.
        release_s: Instant the raw data becomes available on ``origin``, in seconds.
        deadline_s: Absolute instant by which the final output must reach the ground station.
        raw_size_gb: Size of the raw data, in Gb.
        tasks: The pipeline, in execution order.
    """

    id: str
    priority: Priority
    origin: NodeId
    arrival_s: float
    release_s: float
    deadline_s: float
    raw_size_gb: float
    tasks: tuple[TaskSpec, ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise ScenarioError("l'identificativo della richiesta non può essere vuoto")
        if not self.tasks:
            raise ScenarioError(
                f"richiesta {self.id}: la pipeline deve avere almeno un task"
            )
        _require_finite_at_least(self.arrival_s, 0.0, f"richiesta {self.id}, arrivo")
        _require_finite_at_least(self.release_s, 0.0, f"richiesta {self.id}, rilascio")
        _require_finite_at_least(
            self.deadline_s, self.release_s, f"richiesta {self.id}, scadenza"
        )
        if not (math.isfinite(self.raw_size_gb) and self.raw_size_gb > 0):
            raise ScenarioError(
                f"richiesta {self.id}: la dimensione del raw deve essere finita e > 0"
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
