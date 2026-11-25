"""Generation of the requests from the workload model, each quantity on its own stream.

Each random quantity draws from a stream of its own, so changing the distribution of one does
not change the numbers of the others, and two runs with the same seed and different planners
see the same workload (common random numbers).
"""

from __future__ import annotations

from satedge_simulator.domain.topology import Constellation, NodeId
from satedge_simulator.domain.workload import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.workload_model import Range, WorkloadModel
from satedge_simulator.errors import ScenarioError
from satedge_simulator.rng.rngs import MultiStreamRng
from satedge_simulator.rng.rvgs import bernoulli, equilikely, exponential, uniform

ARRIVALS = 0
PRIORITY = 1
ACQUISITION = 2
ORIGIN = 3
RAW = 4
STAGES = 5
WORK = 6
RATIO = 7
FINAL = 8
"""The stream of each quantity."""


class RequestGenerator:
    """Draws the interarrival times and the requests of the workload model.

    Every task fits strictly in one computing window: the number of stages is drawn, then
    raised to the smallest one with which every task fits, whatever the intermediate outputs
    turn out to be. The window is the shortest full window of the constellation, read and write
    at the slowest HPC rate.

    Raises:
        ScenarioError: If an origin is not a satellite, or if even the largest number of stages
            cannot make every task fit in a window.
    """

    def __init__(
        self, model: WorkloadModel, constellation: Constellation, rng: MultiStreamRng
    ) -> None:
        self._model = model
        satellites = constellation.satellites
        self._origins = model.origins or tuple(
            s.id for s in satellites if not _is_com(constellation, s.id)
        )
        for node in self._origins:
            if not constellation.is_satellite(node):
                raise ScenarioError(f"satellite di origine sconosciuto {node!r}")
        self._window_s = min(
            max((w.duration for w in s.hpc_windows), default=0.0) for s in satellites
        )
        self._rate_gbps = min(s.hpc_rate_gbps for s in satellites)
        self._streams = {i: rng.stream(i) for i in range(FINAL + 1)}
        self._count = 0
        worst = self._fewest_stages(model.raw_size_gb.high, model.work_s_per_gb.high)
        if worst is None:
            raise ScenarioError(
                f"con questi parametri un task può superare la finestra di calcolo di "
                f"{self._window_s:g} s anche con {model.stages[1]} stadi"
            )

    @property
    def window_s(self) -> float:
        """The computing window every task must fit in."""
        return self._window_s

    def next_interarrival_s(self) -> float:
        """Seconds to the next arrival."""
        return exponential(self._streams[ARRIVALS], self._model.mean_interarrival_s)

    def request(self, arrival_s: float) -> RequestSpec:
        """A new request that reaches the ground segment at ``arrival_s``."""
        m = self._model
        self._count += 1
        urgent = m.urgent_probability > 0 and (
            m.urgent_probability >= 1
            or bernoulli(self._streams[PRIORITY], m.urgent_probability) == 1
        )
        priority = Priority.URGENT if urgent else Priority.NON_URGENT
        release = arrival_s + self._draw(ACQUISITION, m.acquisition_delay_s)
        origin = self._origins[
            equilikely(self._streams[ORIGIN], 0, len(self._origins) - 1)
        ]
        raw = self._draw(RAW, m.raw_size_gb)
        work_per_gb = self._draw(WORK, m.work_s_per_gb)
        drawn = equilikely(self._streams[STAGES], *m.stages)
        fewest = self._fewest_stages(raw, work_per_gb)
        assert (
            fewest is not None
        )  # guaranteed by the worst case checked at construction
        stages = max(drawn, fewest)
        execution = work_per_gb * raw / stages
        tasks = []
        size = raw
        for k in range(stages):
            last = k == stages - 1
            size = (
                self._draw(FINAL, m.final_output_gb)
                if last
                else size * self._draw(RATIO, m.intermediate_ratio)
            )
            tasks.append(TaskSpec(execution_s=execution, output_size_gb=size))
        return RequestSpec(
            id=f"G{self._count}",
            priority=priority,
            origin=origin,
            arrival_s=arrival_s,
            release_s=release,
            deadline_s=release + m.deadline_after_release_s[priority],
            raw_size_gb=raw,
            tasks=tuple(tasks),
        )

    def _fewest_stages(self, raw_gb: float, work_s_per_gb: float) -> int | None:
        """The fewest stages, within the bounds, with which every task fits in the window.

        The check takes the largest intermediate ratio, so it holds for any drawn output.
        """
        low, high = self._model.stages
        ratio = self._model.intermediate_ratio.high
        final = self._model.final_output_gb.high
        for stages in range(low, high + 1):
            execution = work_s_per_gb * raw_gb / stages
            size_in = raw_gb
            fits = True
            for k in range(stages):
                size_out = final if k == stages - 1 else size_in * ratio
                occupancy = (size_in + size_out) / self._rate_gbps + execution
                if occupancy >= self._window_s:
                    fits = False
                    break
                size_in = size_out
            if fits:
                return stages
        return None

    def _draw(self, stream: int, r: Range) -> float:
        if r.low == r.high:
            return r.low
        return uniform(self._streams[stream], r.low, r.high)


def _is_com(constellation: Constellation, node: NodeId) -> bool:
    return any(plane.com == node for plane in constellation.planes)
