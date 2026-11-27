"""The observations of one run: per request, at the instant each one is known, and over time.

Per request (a discrete-time series, indexed by the requests):

- ``response_s``: delivery minus release, at the delivery;
- ``acceptance``: 1 if accepted, 0 if rejected, at the decision;
- ``on_time``: for an accepted request, 1 if delivered by its deadline, 0 if late or failed, at
  the instant it ends.

Over time (a continuous-time process):

- ``hpc_utilization``: the time the HPCs are held over the time their windows are open;
- ``plmm_occupancy_gb``: the memory occupied in all the PLMMs.

A request still open at the end has no observation: what is not known by the end is not
observed, as in the real system.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from satedge_simulator.domain.intervals import Window
from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.topology import Constellation, NodeId
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import PlmmChanged, TaskEnded, TaskStarted


class Statistic(StrEnum):
    """A statistic of the output analysis."""

    RESPONSE = "response_s"
    ACCEPTANCE = "acceptance"
    ON_TIME = "on_time"
    HPC_UTILIZATION = "hpc_utilization"
    PLMM_OCCUPANCY = "plmm_occupancy_gb"

    @property
    def per_request(self) -> bool:
        """Whether the statistic is observed once per request, rather than over time."""
        return self in PER_REQUEST


PER_REQUEST = frozenset({Statistic.RESPONSE, Statistic.ACCEPTANCE, Statistic.ON_TIME})
"""The statistics observed once per request."""


@dataclass(frozen=True, slots=True)
class Observation:
    """One value of a per-request statistic, at the instant it became known."""

    time_s: float
    value: float


class TimeSeriesCollector:
    """Records, from the notifications, when each HPC is held and how full the PLMMs are."""

    def __init__(self) -> None:
        self._since: dict[tuple[str, int, NodeId], float] = {}
        self._busy: list[tuple[float, float]] = []
        self._levels: dict[NodeId, float] = {}
        self._steps: list[tuple[float, float]] = []

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(TaskStarted, self._started)
        bus.subscribe(TaskEnded, self._ended)
        bus.subscribe(PlmmChanged, self._changed)

    def busy(self, end_s: float) -> tuple[tuple[float, float], ...]:
        """The intervals in which an HPC was held; one still held at the end closes there."""
        still = tuple((since, end_s) for since in self._since.values())
        return (*self._busy, *still)

    @property
    def plmm_steps(self) -> tuple[tuple[float, float], ...]:
        """``(instant, total occupied memory from that instant)``, in time order."""
        return tuple(self._steps)

    def _started(self, n: TaskStarted) -> None:
        self._since[(n.request_id, n.task_index, n.satellite)] = n.time

    def _ended(self, n: TaskEnded) -> None:
        self._busy.append(
            (self._since.pop((n.request_id, n.task_index, n.satellite)), n.time)
        )

    def _changed(self, n: PlmmChanged) -> None:
        self._levels[n.satellite] = n.level_gb
        total = sum(self._levels.values())
        if self._steps and self._steps[-1][0] == n.time:
            self._steps[-1] = (
                n.time,
                total,
            )  # several changes at one instant: keep the last
        else:
            self._steps.append((n.time, total))


class RunObservations:
    """Every observation of one run, and the mean of each statistic over any interval."""

    def __init__(
        self,
        per_request: Mapping[Statistic, tuple[Observation, ...]],
        busy: Iterable[tuple[float, float]],
        windows: Iterable[Window],
        plmm_steps: Iterable[tuple[float, float]],
        end_s: float,
    ) -> None:
        self._per_request = MappingProxyType(
            {
                s: tuple(sorted(obs, key=lambda o: o.time_s))
                for s, obs in per_request.items()
            }
        )
        self._busy = tuple(busy)
        self._windows = tuple(windows)
        self._steps = tuple(plmm_steps)
        self._step_times = [t for t, _ in self._steps]
        self.end_s = end_s

    @classmethod
    def of_run(
        cls,
        records: Mapping[str, RequestRecord],
        requests: Iterable[RequestSpec],
        collector: TimeSeriesCollector,
        constellation: Constellation,
        end_s: float,
    ) -> RunObservations:
        """The observations of a run, from its final records and its time series."""
        windows = [w for s in constellation.satellites for w in s.hpc_windows]
        return cls(
            _per_request(records, requests),
            collector.busy(end_s),
            windows,
            collector.plmm_steps,
            end_s,
        )

    def observations(self, statistic: Statistic) -> tuple[Observation, ...]:
        """The observations of a per-request statistic, in time order."""
        return self._per_request.get(statistic, ())

    def mean(self, statistic: Statistic, start_s: float, end_s: float) -> float | None:
        """The mean of ``statistic`` over ``[start_s, end_s)``.

        Per request: the mean of the observations made in the interval. Over time: the time
        average over the interval. ``None`` when there is nothing to average: no observation,
        or no computing window open.
        """
        if statistic is Statistic.HPC_UTILIZATION:
            available = sum(
                _overlap(w.start, w.end, start_s, end_s) for w in self._windows
            )
            if available <= 0.0:
                return None
            held = sum(_overlap(a, b, start_s, end_s) for a, b in self._busy)
            return held / available
        if statistic is Statistic.PLMM_OCCUPANCY:
            return self._time_average_plmm(start_s, end_s)
        values = [
            o.value for o in self.observations(statistic) if start_s <= o.time_s < end_s
        ]
        return sum(values) / len(values) if values else None

    def _time_average_plmm(self, start_s: float, end_s: float) -> float | None:
        if end_s <= start_s:
            return None
        k = bisect.bisect_right(self._step_times, start_s) - 1
        level = self._steps[k][1] if k >= 0 else 0.0
        area = 0.0
        t = start_s
        for time, total in self._steps[k + 1 :]:
            if time >= end_s:
                break
            area += level * (time - t)
            t, level = time, total
        area += level * (end_s - t)
        return area / (end_s - start_s)


def _per_request(
    records: Mapping[str, RequestRecord], requests: Iterable[RequestSpec]
) -> dict[Statistic, tuple[Observation, ...]]:
    specs = {r.id: r for r in requests}
    response: list[Observation] = []
    acceptance: list[Observation] = []
    on_time: list[Observation] = []
    for request_id, record in records.items():
        for at, status in record.history:
            if status is RequestStatus.ACCEPTED:
                acceptance.append(Observation(at, 1.0))
            elif status is RequestStatus.REJECTED:
                acceptance.append(Observation(at, 0.0))
        at, final = record.history[-1]
        if final in (RequestStatus.DELIVERED_ON_TIME, RequestStatus.DELIVERED_LATE):
            response.append(Observation(at, at - specs[request_id].release_s))
        if final in (
            RequestStatus.DELIVERED_ON_TIME,
            RequestStatus.DELIVERED_LATE,
            RequestStatus.FAILED,
        ):
            on_time.append(
                Observation(
                    at, 1.0 if final is RequestStatus.DELIVERED_ON_TIME else 0.0
                )
            )
    return {
        Statistic.RESPONSE: tuple(response),
        Statistic.ACCEPTANCE: tuple(acceptance),
        Statistic.ON_TIME: tuple(on_time),
    }


def _overlap(a: float, b: float, start: float, end: float) -> float:
    return max(0.0, min(b, end) - max(a, start))
