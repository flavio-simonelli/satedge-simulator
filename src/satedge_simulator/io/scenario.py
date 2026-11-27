"""Scenario file: the paths to the files that describe the scheduler, the workload, the satellites
and the topology, read together and checked against each other.

This module reads the documents only. The objects of the simulation are built from them by
:mod:`satedge_simulator.loading.scenario`.
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
    """A scenario file. Every path is relative to the file that contains it."""

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
    """Read the scenario in ``path`` and the four files it names, and check them together.

    Raises:
        DocumentError: If a file cannot be read or is not valid, or if the files do not agree
            with each other. The message names the file.
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
    """The names used by one file must be defined by the others.

    This is about the references only: whether a value is meaningful is for the domain.
    """
    nodes = {node.name: node for plane in files.topology.planes for node in plane.nodes}
    for node in nodes.values():
        if node.type not in files.satellites:
            raise DocumentError(
                f"{path}: node {node.name} has the type {node.type!r}, "
                "which the satellites file does not define"
            )
    if isinstance(files.workload, ExplicitWorkloadDoc):
        for request in files.workload.requests:
            if request.origin not in nodes:
                raise DocumentError(
                    f"{path}: request {request.id} starts from {request.origin!r}, "
                    "which is not a satellite of the topology"
                )
