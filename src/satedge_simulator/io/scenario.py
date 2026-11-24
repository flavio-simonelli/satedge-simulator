"""Scenario file: the file that names the topology, the contact plan, the workload and the solver."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import field_validator

from satedge_simulator.domain.scenario import Scenario, SimulationSettings
from satedge_simulator.errors import DocumentError, ScenarioError
from satedge_simulator.io.base import Document, check_schema_version, read_document
from satedge_simulator.io.contact_plan import load_contact_plan
from satedge_simulator.io.topology import load_topology
from satedge_simulator.io.workload import load_workload


class PlannerDoc(Document):
    """The planner: the solver file, and the computing budget before each contact."""

    solver: str
    lead_time_s: float | None = None


class SimulationDoc(Document):
    """How the execution is run."""

    end_s: float
    tolerance_s: float = 1e-4
    strict: bool = False


class ScenarioDoc(Document):
    """A scenario file. The paths are relative to the file that contains them."""

    schema_version: str
    topology: str
    contact_plan: str
    workload: str
    planner: PlannerDoc
    simulation: SimulationDoc

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


@dataclass(frozen=True, slots=True)
class LoadedScenario:
    """A scenario read from its files.

    Attributes:
        scenario: The simulation to run.
        solver_path: The solver file. It is read by the planner, which is chosen separately.
    """

    scenario: Scenario
    solver_path: Path


def load_scenario(path: str | Path) -> LoadedScenario:
    """Read the scenario in ``path`` and every file it names.

    Raises:
        DocumentError: If a file cannot be read or is not valid, or if the scenario is not
            consistent. The message names the file.
    """
    document = read_document(path, ScenarioDoc)
    base = Path(path).parent
    contact_plan = load_contact_plan(base / document.contact_plan)
    constellation = load_topology(base / document.topology, contact_plan)
    requests = load_workload(base / document.workload)
    solver_path = base / document.planner.solver
    if not solver_path.is_file():
        raise DocumentError(
            f"{path}: the solver file {document.planner.solver!r} does not exist"
        )
    try:
        scenario = Scenario(
            constellation=constellation,
            requests=requests,
            settings=SimulationSettings(
                end_s=document.simulation.end_s,
                tolerance_s=document.simulation.tolerance_s,
                strict=document.simulation.strict,
            ),
            lead_time_s=document.planner.lead_time_s,
        )
    except ScenarioError as error:
        raise DocumentError(f"{path}: {error}") from error
    return LoadedScenario(scenario, solver_path)
