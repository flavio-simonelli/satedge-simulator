"""Scenario file: the paths of the scheduler, workload, satellites and topology files.

This module reads the five files together and checks some of the names that one file takes from
another: the types of the satellites, and the origins of the explicit requests.

It reads the documents only. The objects of the domain are built from them by
:mod:`satedge_simulator.io.loading.scenario`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from satedge_simulator.errors import DocumentError
from satedge_simulator.io.base import VersionedDocument, read_document
from satedge_simulator.io.satellites import SatelliteTypeDoc, load_satellites
from satedge_simulator.io.scheduler import SchedulerDoc, SchedulerFile
from satedge_simulator.io.topology import TopologyDoc, read_topology
from satedge_simulator.io.workload import ExplicitWorkloadDoc, WorkloadDoc, WorkloadFile


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
class ScenarioFiles:
    """The documents of a scenario, and of the four files it names.

    Attributes:
        scenario: The scenario file.
        scheduler: The scheduler file.
        workload: The workload file, explicit or stochastic.
        satellites: The satellite types, by name.
        topology: The topology file.
    """

    scenario: ScenarioDoc
    scheduler: SchedulerDoc
    workload: WorkloadDoc
    satellites: dict[str, SatelliteTypeDoc]
    topology: TopologyDoc


def read_scenario(path: str | Path) -> ScenarioFiles:
    """Read the scenario in ``path`` and the four files it names, and check their references.

    Raises:
        DocumentError: If a file cannot be read or is not valid, if a satellite has a type that
            the satellites file does not define, or if an explicit request starts from a name
            that is not a satellite of the topology. The message names a file.
    """
    scenario = read_document(path, ScenarioDoc)
    base = Path(path).parent
    files = ScenarioFiles(
        scenario=scenario,
        scheduler=SchedulerFile.read(base / scenario.scheduler),
        workload=WorkloadFile.read(base / scenario.workload),
        satellites=load_satellites(base / scenario.satellites),
        topology=read_topology(base / scenario.topology),
    )
    _check_references(path, files)
    return files


def _check_references(path: str | Path, files: ScenarioFiles) -> None:
    """Check that the satellite types and the request origins are defined."""
    nodes = [node for plane in files.topology.planes for node in plane.nodes]
    for node in nodes:
        if node.type not in files.satellites:
            raise DocumentError(
                f"{path}: node {node.name} has the type {node.type!r}, "
                "which the satellites file does not define"
            )
    if isinstance(files.workload, ExplicitWorkloadDoc):
        names = {node.name for node in nodes}
        for request in files.workload.requests:
            if request.origin not in names:
                raise DocumentError(
                    f"{path}: request {request.id} starts from {request.origin!r}, "
                    "which is not a satellite of the topology"
                )
