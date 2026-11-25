"""The stochastic model of the workload: the distribution of every quantity of a request.

No data on the real workload is available, so each choice rests on the mechanism behind the
quantity, and every parameter can be changed in the scenario:

- arrivals at the ground segment: a Poisson process, the superposition of many independent
  users (Palm-Khintchine);
- priority class: Bernoulli, an independent marking that splits the arrivals into two
  independent Poisson processes;
- acquisition delay, from the arrival to the release of the raw data: Uniform(0, revisit), the
  random phase of the orbit at the instant of the request;
- origin satellite: equally likely among the satellites that acquire images;
- raw data: Uniform over the range of the case study, the maximum entropy choice when only the
  bounds are known;
- pipeline: the L0 to L1 processing split into 1 to 3 sequential stages (as L1A, L1B, L1C),
  finer when needed so that every task fits in one computing window;
- work: proportional to the raw data, as a per-pixel processing, split evenly among the stages;
- intermediate outputs: about the size of their input, since the L1 corrections transform the
  image without reducing it; final output: the extracted information, below 1 Mb;
- deadline: a fixed delay after the release, per class.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.domain.workload import Priority
from satedge_simulator.errors import ScenarioError

ORBITAL_PERIOD_S = 5640.0
"""94 minutes: the default revisit time, and the period of the computing windows."""


@dataclass(frozen=True, slots=True)
class Range:
    """A closed range ``[low, high]``; a degenerate one, ``low == high``, is a constant."""

    low: float
    high: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.low) and math.isfinite(self.high)):
            raise ScenarioError(
                f"intervallo [{self.low}, {self.high}]: gli estremi devono essere finiti"
            )
        if self.low > self.high:
            raise ScenarioError(
                f"intervallo [{self.low}, {self.high}]: serve low <= high"
            )


@dataclass(frozen=True, slots=True)
class WorkloadModel:
    """The parameters of the stochastic workload.

    Attributes:
        arrivals_per_hour: Rate of the Poisson arrivals at the ground segment.
        urgent_probability: Probability that a request is urgent.
        acquisition_delay_s: Delay from the arrival to the release of the raw data.
        origins: The satellites that acquire images; ``None`` means every satellite that is
            not the COM of its plane.
        raw_size_gb: Size of the raw data.
        stages: Bounds on the number of tasks of the pipeline.
        work_s_per_gb: Execution time of the whole pipeline per Gb of raw data.
        intermediate_ratio: Size of an intermediate output over the size of its input.
        final_output_gb: Size of the final output.
        deadline_after_release_s: Delay after the release within which each class must be
            delivered.
    """

    arrivals_per_hour: float
    urgent_probability: float = 0.5
    acquisition_delay_s: Range = field(
        default_factory=lambda: Range(0.0, ORBITAL_PERIOD_S)
    )
    origins: tuple[NodeId, ...] | None = None
    raw_size_gb: Range = field(default_factory=lambda: Range(2.0, 12.0))
    stages: tuple[int, int] = (1, 3)
    work_s_per_gb: Range = field(default_factory=lambda: Range(12.0, 24.0))
    intermediate_ratio: Range = field(default_factory=lambda: Range(0.8, 1.2))
    final_output_gb: Range = field(default_factory=lambda: Range(0.0001, 0.001))
    deadline_after_release_s: Mapping[Priority, float] = field(
        default_factory=lambda: {Priority.URGENT: 7200.0, Priority.NON_URGENT: 25200.0}
    )

    def __post_init__(self) -> None:
        if not (math.isfinite(self.arrivals_per_hour) and self.arrivals_per_hour > 0):
            raise ScenarioError(
                f"il tasso di arrivo deve essere finito e > 0, invece è {self.arrivals_per_hour}"
            )
        if not 0.0 <= self.urgent_probability <= 1.0:
            raise ScenarioError(
                f"la probabilità di una richiesta urgente deve essere tra 0 e 1, invece è "
                f"{self.urgent_probability}"
            )
        _require_positive(self.raw_size_gb, "dimensione del raw")
        _require_positive(self.work_s_per_gb, "lavoro per Gb")
        _require_positive(self.intermediate_ratio, "rapporto degli output intermedi")
        _require_positive(self.final_output_gb, "dimensione dell'output finale")
        if self.acquisition_delay_s.low < 0:
            raise ScenarioError("il ritardo di acquisizione non può essere negativo")
        low, high = self.stages
        if not 1 <= low <= high:
            raise ScenarioError(
                f"stadi della pipeline: serve 1 <= minimo <= massimo, invece {self.stages}"
            )
        if self.origins is not None and not self.origins:
            raise ScenarioError("la lista dei satelliti che acquisiscono è vuota")
        if set(self.deadline_after_release_s) != set(Priority):
            raise ScenarioError("serve la scadenza di ogni classe di priorità")
        if any(d <= 0 for d in self.deadline_after_release_s.values()):
            raise ScenarioError("le scadenze devono essere > 0")
        object.__setattr__(
            self,
            "deadline_after_release_s",
            MappingProxyType(dict(self.deadline_after_release_s)),
        )

    @property
    def mean_interarrival_s(self) -> float:
        return 3600.0 / self.arrivals_per_hour


def _require_positive(r: Range, what: str) -> None:
    if r.low <= 0:
        raise ScenarioError(
            f"{what}: gli estremi devono essere > 0, invece [{r.low}, {r.high}]"
        )
