"""The section ``workload_model`` of a scenario: the parameters of the stochastic workload.

Only the arrival rate is required. A field left out keeps the default of
:class:`~satedge_simulator.domain.workload_model.WorkloadModel`, which is the only place the
defaults are written. A range is written ``[low, high]``.
"""

from __future__ import annotations

from typing import Any

from satedge_simulator.domain.workload import Priority
from satedge_simulator.domain.workload_model import Range, WorkloadModel
from satedge_simulator.io.base import Document

_RANGES = (
    "acquisition_delay_s",
    "raw_size_gb",
    "work_s_per_gb",
    "intermediate_ratio",
    "final_output_gb",
)


class DeadlinesDoc(Document):
    """Delay after the release within which each class must be delivered, in seconds."""

    urgent: float
    non_urgent: float


class WorkloadModelDoc(Document):
    """The parameters of the stochastic workload, as the scenario writes them."""

    arrivals_per_hour: float
    urgent_probability: float | None = None
    acquisition_delay_s: tuple[float, float] | None = None
    origins: list[str] | None = None
    raw_size_gb: tuple[float, float] | None = None
    stages: tuple[int, int] | None = None
    work_s_per_gb: tuple[float, float] | None = None
    intermediate_ratio: tuple[float, float] | None = None
    final_output_gb: tuple[float, float] | None = None
    deadline_after_release_s: DeadlinesDoc | None = None

    def to_model(self) -> WorkloadModel:
        """The model of the domain, with its defaults for the fields left out.

        Raises:
            ScenarioError: If a parameter is out of range.
        """
        given: dict[str, Any] = self.model_dump(
            exclude_none=True, exclude={"deadline_after_release_s"}
        )
        for name in _RANGES:
            if name in given:
                given[name] = Range(*given[name])
        if "origins" in given:
            given["origins"] = tuple(given["origins"])
        deadlines = self.deadline_after_release_s
        if deadlines is not None:
            given["deadline_after_release_s"] = {
                Priority.URGENT: deadlines.urgent,
                Priority.NON_URGENT: deadlines.non_urgent,
            }
        return WorkloadModel(**given)
