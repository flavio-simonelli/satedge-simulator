"""Scenario file: only the paths to the files that describe the scheduler, the workload, the satellites and the topology."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pydantic import field_validator

from satedge_simulator.domain.scenario import Scenario
from satedge_simulator.io.base import Document, check_schema_version, read_document


class ScenarioDoc(Document):
    """A scenario file. Every path is relative to the file that contains it."""

    schema_version: str
    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    scheduler: str
    workload: str
    satellites: str
    topology: str

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value, cls.SUPPORTED_VERSION)


@dataclass(frozen=True, slots=True)
class LoadedScenario:
    """A scenario read from its files.

    Attributes:
        scenario: The simulation to run.
        solver_path: The scheduler file. It is read by the planner, which is chosen separately.
    """

    scenario: Scenario
    solver_path: Path


def load_scenario(path: str | Path) -> LoadedScenario:
    """Read the scenario file in ``path``.

    Raises:
        DocumentError: If the file cannot be read or is not valid.
        NotImplementedError: Always, for now: the scenario only names the files, and building
            the simulation from them is not written yet.
    """
    read_document(path, ScenarioDoc)
    raise NotImplementedError(
        "load_scenario: building the simulation from the paths of the scenario is not "
        "implemented yet"
    )
