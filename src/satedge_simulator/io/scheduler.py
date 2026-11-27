"""Scheduler file: the planner the scenario uses, its method, its deadlines and its lead time.

The method is the sequential heuristic, or the MILP, and it is the discriminator of the file. Only
the MILP has a time limit, so the time limit is one of its parameters.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, ClassVar, Literal

from pydantic import Field, RootModel

from satedge_simulator.io.base import VersionedDocument, read_document


class SchedulerMethod(StrEnum):
    """The planning method."""

    SEQUENTIAL = "sequential"
    MILP = "milp"


class DeadlineKind(StrEnum):
    """Whether a missed deadline makes a request infeasible, or only counts as a late delivery."""

    HARD = "hard"
    SOFT = "soft"


class SequentialSchedulerDoc(VersionedDocument):
    """The sequential heuristic. It has no time limit, so its result is ready when it finishes.

    ``lead_time_s`` is how long before a contact the scheduling starts. It is required, since
    there is no time limit to take its place.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    method: Literal[SchedulerMethod.SEQUENTIAL]
    deadline: DeadlineKind
    lead_time_s: float = Field(gt=0)


class MilpSchedulerDoc(VersionedDocument):
    """The MILP, with its level, its warm start and its time limit.

    ``lead_time_s`` may be left out: it is then the time limit. ``level`` is the level of the
    MILP, with the capacity of the PLMM. ``warm_start`` says whether the MILP starts from the
    solution of the sequential heuristic.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    method: Literal[SchedulerMethod.MILP]
    deadline: DeadlineKind
    lead_time_s: float | None = Field(default=None, gt=0)
    level: int
    warm_start: bool
    time_limit_s: float = Field(gt=0)


class SchedulerDoc(
    RootModel[
        Annotated[
            SequentialSchedulerDoc | MilpSchedulerDoc, Field(discriminator="method")
        ]
    ]
):
    """A scheduler file: the sequential heuristic or the MILP, chosen by ``method``."""


def read_scheduler(
    path: str | Path,
) -> SequentialSchedulerDoc | MilpSchedulerDoc:
    """Read and validate the scheduler file in ``path``.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema. The message
            names the file.
    """
    return read_document(path, SchedulerDoc).root
