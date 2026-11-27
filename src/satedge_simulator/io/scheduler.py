"""Scheduler file: the planner the scenario uses, its method, its deadlines and its lead time.

The method is the sequential heuristic, or the MILP, and it is the discriminator of the file. Only
the MILP has a time limit, so the time limit is one of its parameters.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field

from satedge_simulator.io.base import Registry, VersionedDocument, read_variant


class SchedulerMethod(StrEnum):
    """The planning method."""

    SEQUENTIAL = "sequential"
    MILP = "milp"


class DeadlineKind(StrEnum):
    """Whether a missed deadline makes a request infeasible, or only counts as a late delivery."""

    HARD = "hard"
    SOFT = "soft"


class SchedulerDoc(VersionedDocument):
    """A scheduler file, whatever its method: what every method has.

    Each method is a subclass, registered in :data:`SCHEDULERS` under its method name.
    """

    deadline: DeadlineKind


SCHEDULERS: Registry[SchedulerDoc] = Registry("method")


@SCHEDULERS.variant("sequential")
class SequentialSchedulerDoc(SchedulerDoc):
    """The sequential heuristic. It has no time limit, so its result is ready when it finishes.

    ``lead_time_s`` is how long before a contact the scheduling starts. It is required, since
    there is no time limit to take its place.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    method: Literal[SchedulerMethod.SEQUENTIAL]
    lead_time_s: float = Field(gt=0)


@SCHEDULERS.variant("milp")
class MilpSchedulerDoc(SchedulerDoc):
    """The MILP, with its level, its warm start and its time limit.

    ``lead_time_s`` may be left out: it is then the time limit. ``level`` is the level of the
    MILP, with the capacity of the PLMM. ``warm_start`` says whether the MILP starts from the
    solution of the sequential heuristic.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    method: Literal[SchedulerMethod.MILP]
    lead_time_s: float | None = Field(default=None, gt=0)
    level: int
    warm_start: bool
    time_limit_s: float = Field(gt=0)


class SchedulerFile:
    """The scheduler file: the reader of the variants registered in :data:`SCHEDULERS`."""

    @classmethod
    def read(cls, path: str | Path) -> SchedulerDoc:
        """Read and validate the scheduler file in ``path``, as the variant it names.

        Raises:
            DocumentError: If the file cannot be read, does not match the schema of its method and
                version, or names no known method. The message names the file.
        """
        return read_variant(path, SCHEDULERS)
