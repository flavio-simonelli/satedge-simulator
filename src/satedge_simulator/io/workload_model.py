"""The section ``workload_model`` of a scenario: the parameters of the stochastic workload.

Every field has the default of the model; a range is written ``[low, high]``.
"""

from __future__ import annotations

from satedge_simulator.domain.workload import Priority
from satedge_simulator.domain.workload_model import (
    ORBITAL_PERIOD_S,
    Range,
    WorkloadModel,
)
from satedge_simulator.io.base import Document


class DeadlinesDoc(Document):
    """Delay after the release within which each class must be delivered, in seconds."""

    urgent: float = 7200.0
    non_urgent: float = 25200.0


class WorkloadModelDoc(Document):
    """The parameters of the stochastic workload, as the scenario writes them."""

    arrivals_per_hour: float
    urgent_probability: float = 0.5
    acquisition_delay_s: tuple[float, float] = (0.0, ORBITAL_PERIOD_S)
    origins: list[str] | None = None
    raw_size_gb: tuple[float, float] = (2.0, 12.0)
    stages: tuple[int, int] = (1, 3)
    work_s_per_gb: tuple[float, float] = (12.0, 24.0)
    intermediate_ratio: tuple[float, float] = (0.8, 1.2)
    final_output_gb: tuple[float, float] = (0.0001, 0.001)
    deadline_after_release_s: DeadlinesDoc = DeadlinesDoc()

    def to_model(self) -> WorkloadModel:
        """The model of the domain.

        Raises:
            ScenarioError: If a parameter is out of range.
        """
        deadlines = self.deadline_after_release_s
        return WorkloadModel(
            arrivals_per_hour=self.arrivals_per_hour,
            urgent_probability=self.urgent_probability,
            acquisition_delay_s=Range(*self.acquisition_delay_s),
            origins=tuple(self.origins) if self.origins is not None else None,
            raw_size_gb=Range(*self.raw_size_gb),
            stages=self.stages,
            work_s_per_gb=Range(*self.work_s_per_gb),
            intermediate_ratio=Range(*self.intermediate_ratio),
            final_output_gb=Range(*self.final_output_gb),
            deadline_after_release_s={
                Priority.URGENT: deadlines.urgent,
                Priority.NON_URGENT: deadlines.non_urgent,
            },
        )
