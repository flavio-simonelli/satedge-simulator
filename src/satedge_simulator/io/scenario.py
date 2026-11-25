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
from satedge_simulator.io.workload_model import WorkloadModelDoc
from satedge_simulator.rng.rngs import DEFAULT_SEED


class PlannerDoc(Document):
    """The planner: the solver file, and the computing budget before each contact."""

    solver: str
    lead_time_s: float | None = None


class SimulationDoc(Document):
    """How the execution is run."""

    end_s: float
    tolerance_s: float = 1e-4
    strict: bool = False
    seed: int = DEFAULT_SEED


class ScenarioDoc(Document):
    """A scenario file. The paths are relative to the file that contains them.

    The workload is a file of requests, a stochastic model, or both: at least one is needed.
    """

    schema_version: str
    topology: str
    contact_plan: str
    workload: str | None = None
    workload_model: WorkloadModelDoc | None = None
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
    contact_plan = load_contact_plan(
        base / document.contact_plan, horizon_s=document.simulation.end_s
    )
    constellation = load_topology(
        base / document.topology, contact_plan, horizon_s=document.simulation.end_s
    )
    if document.workload is None and document.workload_model is None:
        raise DocumentError(
            f"{path}: serve un carico, nel file indicato da 'workload' o nel modello "
            "'workload_model'"
        )
    requests = (
        load_workload(base / document.workload) if document.workload is not None else ()
    )
    solver_path = base / document.planner.solver
    if not solver_path.is_file():
        raise DocumentError(
            f"{path}: il file del solver {document.planner.solver!r} non esiste"
        )
    try:
        scenario = Scenario(
            constellation=constellation,
            requests=requests,
            settings=SimulationSettings(
                end_s=document.simulation.end_s,
                tolerance_s=document.simulation.tolerance_s,
                strict=document.simulation.strict,
                seed=document.simulation.seed,
            ),
            lead_time_s=document.planner.lead_time_s,
            workload_model=(
                document.workload_model.to_model()
                if document.workload_model is not None
                else None
            ),
        )
    except ScenarioError as error:
        raise DocumentError(f"{path}: {error}") from error
    return LoadedScenario(scenario, solver_path)
