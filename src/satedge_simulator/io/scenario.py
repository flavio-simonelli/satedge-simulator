"""Scenario file: the paths of the scheduler, workload, satellites and topology files.

This module reads the scenario file only. Each of the files it names is read by its own module,
when whoever needs it asks for it. The names that one of those files takes from another are
checked where the objects of the domain are built, in :mod:`satedge_simulator.io.loading`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from satedge_simulator.io.base import VersionedDocument, read_document


class ScenarioDoc(VersionedDocument):
    """The content of a scenario file. Every path is relative to the directory of that file.

    Attributes:
        schema_version: Version of the format of the file.
        scheduler: Path of the scheduler file.
        workload: Path of the workload file.
        satellites: Path of the satellites file.
        topology: Path of the topology file.
    """

    SUPPORTED_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    scheduler: str
    workload: str
    satellites: str
    topology: str


@dataclass(frozen=True, slots=True)
class ScenarioPaths:
    """The files that a scenario file names, as paths that can be opened.

    Attributes:
        scheduler: The scheduler file.
        workload: The workload file.
        satellites: The satellites file.
        topology: The topology file.
    """

    scheduler: Path
    workload: Path
    satellites: Path
    topology: Path


def read_scenario(path: str | Path) -> ScenarioPaths:
    """Read the scenario file ``path``, and give the paths of the files it names. Those files
    are not opened.

    Raises:
        DocumentError: If the format is unknown, the file cannot be read, its text is not valid
            in its format, it does not match the schema, or its version is not supported. The
            message names the file.
    """
    document = read_document(path, ScenarioDoc)
    base = Path(path).parent
    return ScenarioPaths(
        scheduler=base / document.scheduler,
        workload=base / document.workload,
        satellites=base / document.satellites,
        topology=base / document.topology,
    )
