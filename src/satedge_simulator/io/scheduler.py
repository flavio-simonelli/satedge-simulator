"""Scheduler file: the method of the planner, and its parameters.

The ``method`` field says which variant of the file it is: the sequential heuristic, or the MILP.
Each variant has its own fields. The values of the numbers are not checked here.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from satedge_simulator.io.base import Registry, VersionedDocument, read_variant


class SchedulerMethod(StrEnum):
    """The planning method."""

    SEQUENTIAL = "sequential"
    MILP = "milp"


class DeadlineKind(StrEnum):
    """The kind of deadline the planner works with."""

    HARD = "hard"
    SOFT = "soft"


class SchedulerDoc(VersionedDocument):
    """The fields that a scheduler file has with every method.

    Each method is a subclass, registered in :data:`SCHEDULERS` under its method name.

    Attributes:
        schema_version: Version of the format of the file.
        deadline: Whether the deadlines are hard or soft.
    """

    deadline: DeadlineKind


SCHEDULERS: Registry[SchedulerDoc] = Registry("method")


@SCHEDULERS.variant("sequential")
class SequentialSchedulerDoc(SchedulerDoc):
    """The scheduler file of the sequential heuristic.

    Attributes:
        method: Always ``sequential``.
        lead_time_s: Lead time of the planning, in seconds.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    method: Literal[SchedulerMethod.SEQUENTIAL]
    lead_time_s: float


@SCHEDULERS.variant("milp")
class MilpSchedulerDoc(SchedulerDoc):
    """The scheduler file of the MILP.

    Attributes:
        method: Always ``milp``.
        lead_time_s: Lead time of the planning, in seconds. It may be left out.
        level: Level of the MILP.
        warm_start: Whether the MILP starts from a warm start.
        time_limit_s: Time limit of the solver, in seconds.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    method: Literal[SchedulerMethod.MILP]
    lead_time_s: float | None = None
    level: int
    warm_start: bool
    time_limit_s: float


class SchedulerFile:
    """The scheduler file: the reader of the variants registered in :data:`SCHEDULERS`."""

    @classmethod
    def read(cls, path: str | Path) -> SchedulerDoc:
        """Read the scheduler file in ``path``, with the schema of the method it names.

        Raises:
            DocumentError: If the format is unknown, the file cannot be read or its text is not
                valid in its format, it names no known method, it does not match the schema of
                its method, or its version is not supported. The message names the file.
        """
        return read_variant(path, SCHEDULERS)
