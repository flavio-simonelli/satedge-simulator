"""Workload mapping: the explicit requests of a workload document, turned into domain requests.

A stochastic workload is not mapped here: its requests are generated during the run.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from satedge_simulator.domain.quantities import DataSize, Duration, Time
from satedge_simulator.domain.requests import Priority, RequestSpec, TaskSpec
from satedge_simulator.domain.satellite import Satellite
from satedge_simulator.io.loading.conventions import DEFAULT_DEADLINE_AFTER_RELEASE
from satedge_simulator.io.loading.errors import errors_in
from satedge_simulator.io.workload import ExplicitWorkloadDoc, RequestDoc


def build_requests(
    workload: ExplicitWorkloadDoc,
    satellites: Mapping[str, Satellite],
    workload_file: Path,
) -> tuple[RequestSpec, ...]:
    """The requests of ``workload``, in the order the file lists them.

    Every origin must be in ``satellites``, which
    :func:`~satedge_simulator.io.scenario.read_scenario` checks. Without ``arrival_s`` a request
    arrives at its release, and without ``deadline_s`` it has the default delay of its
    priority class after the release. The path is used by the error messages only.

    Raises:
        DocumentError: If a value breaks a rule of the domain. The message names the file and
            the request.
    """
    requests: list[RequestSpec] = []
    for doc in workload.requests:
        with errors_in(workload_file, f"request {doc.id!r}"):
            requests.append(_request(doc, satellites[doc.origin]))
    return tuple(requests)


def _request(doc: RequestDoc, origin: Satellite) -> RequestSpec:
    priority = Priority(doc.priority.value)
    release = Time(doc.release_s)
    arrival = release if doc.arrival_s is None else Time(doc.arrival_s)
    if doc.deadline_s is None:
        deadline = release + DEFAULT_DEADLINE_AFTER_RELEASE[priority]
    else:
        deadline = Time(doc.deadline_s)
    return RequestSpec(
        id=doc.id,
        priority=priority,
        origin=origin,
        arrival=arrival,
        release=release,
        deadline=deadline,
        raw_size=DataSize(doc.raw_size_gb),
        tasks=tuple(
            TaskSpec(Duration(t.execution_s), DataSize(t.output_size_gb))
            for t in doc.tasks
        ),
    )
