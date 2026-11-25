"""Generation of the requests of the workload model, each quantity on its own stream."""

from __future__ import annotations

from satedge_simulator.domain.topology import Constellation, NodeId
from satedge_simulator.domain.workload import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.workload_model import Range, WorkloadModel
from satedge_simulator.errors import ScenarioError
from satedge_simulator.generation.quantities import Quantity
from satedge_simulator.generation.stages import StageSplitter
from satedge_simulator.rng.rngs import MultiStreamRng, Stream
from satedge_simulator.rng.rvgs import bernoulli, equilikely, exponential, uniform


class RequestGenerator:
    """Draws the interarrival times and the requests of the workload model.

    The number of stages of each pipeline comes from a :class:`StageSplitter`, so that every
    task fits strictly in one computing window.

    Raises:
        ScenarioError: If an origin is not a satellite, or if even the largest number of stages
            cannot make every task fit in a window.
    """

    def __init__(
        self, model: WorkloadModel, constellation: Constellation, rng: MultiStreamRng
    ) -> None:
        self._model = model
        self._origins = _origins(model, constellation)
        self._splitter = StageSplitter.for_model(model, constellation)
        self._streams = {q: rng.stream(q) for q in Quantity}
        self._count = 0

    @property
    def window_s(self) -> float:
        """The computing window every task must fit in."""
        return self._splitter.window_s

    def next_interarrival_s(self) -> float:
        """Seconds to the next arrival."""
        return exponential(
            self._stream(Quantity.ARRIVALS), self._model.mean_interarrival_s
        )

    def request(self, arrival_s: float) -> RequestSpec:
        """A new request that reaches the ground segment at ``arrival_s``."""
        m = self._model
        self._count += 1
        priority = self._priority()
        release = arrival_s + self._draw(Quantity.ACQUISITION, m.acquisition_delay_s)
        origin = self._origins[
            equilikely(self._stream(Quantity.ORIGIN), 0, len(self._origins) - 1)
        ]
        raw = self._draw(Quantity.RAW, m.raw_size_gb)
        work_per_gb = self._draw(Quantity.WORK, m.work_s_per_gb)
        drawn = equilikely(self._stream(Quantity.STAGES), *m.stages)
        stages = self._splitter.stages(drawn, raw, work_per_gb)
        return RequestSpec(
            id=f"G{self._count}",
            priority=priority,
            origin=origin,
            arrival_s=arrival_s,
            release_s=release,
            deadline_s=release + m.deadline_after_release_s[priority],
            raw_size_gb=raw,
            tasks=self._tasks(stages, raw, work_per_gb * raw / stages),
        )

    def _priority(self) -> Priority:
        p = self._model.urgent_probability
        if p <= 0.0:
            return Priority.NON_URGENT
        if p >= 1.0 or bernoulli(self._stream(Quantity.PRIORITY), p) == 1:
            return Priority.URGENT
        return Priority.NON_URGENT

    def _tasks(
        self, stages: int, raw_gb: float, execution_s: float
    ) -> tuple[TaskSpec, ...]:
        """The stages of the pipeline: intermediate outputs about the size of their input, and
        the extracted information at the end."""
        tasks = []
        size = raw_gb
        for k in range(stages):
            if k == stages - 1:
                size = self._draw(Quantity.FINAL, self._model.final_output_gb)
            else:
                size *= self._draw(Quantity.RATIO, self._model.intermediate_ratio)
            tasks.append(TaskSpec(execution_s=execution_s, output_size_gb=size))
        return tuple(tasks)

    def _stream(self, quantity: Quantity) -> Stream:
        return self._streams[quantity]

    def _draw(self, quantity: Quantity, r: Range) -> float:
        if r.low == r.high:
            return r.low
        return uniform(self._stream(quantity), r.low, r.high)


def _origins(model: WorkloadModel, constellation: Constellation) -> tuple[NodeId, ...]:
    """The satellites that acquire: the ones of the model, or every satellite but the COMs.

    Raises:
        ScenarioError: If an origin of the model is not a satellite.
    """
    if model.origins is None:
        coms = {plane.com for plane in constellation.planes}
        return tuple(s.id for s in constellation.satellites if s.id not in coms)
    for node in model.origins:
        if not constellation.is_satellite(node):
            raise ScenarioError(f"satellite di origine sconosciuto {node!r}")
    return model.origins
