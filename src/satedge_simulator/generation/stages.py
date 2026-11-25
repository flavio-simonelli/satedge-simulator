"""How many stages a pipeline is split into, so that every task fits in a computing window."""

from __future__ import annotations

from satedge_simulator.domain.topology import Constellation
from satedge_simulator.domain.workload_model import WorkloadModel
from satedge_simulator.errors import ScenarioError, StateError


class StageSplitter:
    """Chooses the number of stages: at least the drawn one, and enough that every task fits.

    A task fits when reading its input, executing and writing its output take strictly less
    than one computing window. The check takes the largest intermediate output and the largest
    final output, so a split that fits does so whatever the drawn outputs turn out to be.

    Args:
        bounds: The fewest and the most stages.
        window_s: The computing window every task must fit in.
        rate_gbps: The rate at which the HPC reads and writes its data.
        worst_ratio: The largest intermediate output over its input.
        worst_final_gb: The largest final output.
    """

    def __init__(
        self,
        bounds: tuple[int, int],
        window_s: float,
        rate_gbps: float,
        worst_ratio: float,
        worst_final_gb: float,
    ) -> None:
        self._bounds = bounds
        self._window_s = window_s
        self._rate_gbps = rate_gbps
        self._worst_ratio = worst_ratio
        self._worst_final_gb = worst_final_gb

    @classmethod
    def for_model(
        cls, model: WorkloadModel, constellation: Constellation
    ) -> StageSplitter:
        """The splitter of ``model`` on ``constellation``.

        The window is the shortest among the full windows of the satellites, the rate the
        slowest HPC: a task that fits there fits on any satellite.

        Raises:
            ScenarioError: If the largest pipeline does not fit even with the most stages.
        """
        satellites = constellation.satellites
        window = min(
            max((w.duration for w in s.hpc_windows), default=0.0) for s in satellites
        )
        splitter = cls(
            bounds=model.stages,
            window_s=window,
            rate_gbps=min(s.hpc_rate_gbps for s in satellites),
            worst_ratio=model.intermediate_ratio.high,
            worst_final_gb=model.final_output_gb.high,
        )
        if splitter.fewest(model.raw_size_gb.high, model.work_s_per_gb.high) is None:
            raise ScenarioError(
                f"con questi parametri un task può superare la finestra di calcolo di "
                f"{window:g} s anche con {model.stages[1]} stadi"
            )
        return splitter

    @property
    def window_s(self) -> float:
        """The computing window every task must fit in."""
        return self._window_s

    def stages(self, drawn: int, raw_gb: float, work_s_per_gb: float) -> int:
        """The stages of a pipeline: the drawn number, raised if a task would not fit.

        Raises:
            StateError: If no number of stages fits, which :meth:`for_model` rules out.
        """
        fewest = self.fewest(raw_gb, work_s_per_gb)
        if fewest is None:
            raise StateError(
                f"nessuna scomposizione fa stare nella finestra una pipeline di {raw_gb:g} Gb"
            )
        return max(drawn, fewest)

    def fewest(self, raw_gb: float, work_s_per_gb: float) -> int | None:
        """The fewest stages within the bounds with which every task fits, if any."""
        low, high = self._bounds
        return next(
            (k for k in range(low, high + 1) if self._fits(k, raw_gb, work_s_per_gb)),
            None,
        )

    def _fits(self, stages: int, raw_gb: float, work_s_per_gb: float) -> bool:
        execution = work_s_per_gb * raw_gb / stages
        size_in = raw_gb
        for k in range(stages):
            size_out = (
                self._worst_final_gb if k == stages - 1 else size_in * self._worst_ratio
            )
            if (size_in + size_out) / self._rate_gbps + execution >= self._window_s:
                return False
            size_in = size_out
        return True
