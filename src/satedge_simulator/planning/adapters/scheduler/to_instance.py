"""Translation of a planning snapshot into a scheduling instance of satedge-workflow-scheduler.

The scheduler has no arc leaving the ground station: it never transmits. The simulator's link is
full duplex, but only the arcs the scheduler accepts are built, the ones towards the ground. The
plan uplink from the ground is planned by the simulator, not by the scheduler.
"""

from __future__ import annotations

from satedge_workflow_scheduler.common.intervals import TimeWindow, WindowSet
from satedge_workflow_scheduler.domain.instance import ProblemInstance
from satedge_workflow_scheduler.domain.network import (
    AlwaysAvailable,
    Arc,
    Availability,
    Network,
    Plane,
    WindowedAvailability,
)
from satedge_workflow_scheduler.domain.nodes import GroundStation, Satellite
from satedge_workflow_scheduler.domain.requests import Priority, Request, Task
from satedge_workflow_scheduler.domain.solution import Schedule, TaskExecution, Transfer

from satedge_simulator.domain.intervals import WindowSet as SimWindowSet
from satedge_simulator.domain.plan import PlannedTask, PlannedTransfer
from satedge_simulator.domain.topology import (
    AlwaysAvailable as SimAlwaysAvailable,
)
from satedge_simulator.domain.topology import (
    Constellation,
    Link,
    NodeId,
)
from satedge_simulator.domain.topology import (
    Satellite as SimSatellite,
)
from satedge_simulator.domain.topology import (
    WindowedAvailability as SimWindowedAvailability,
)
from satedge_simulator.domain.workload import RequestSpec
from satedge_simulator.planning.ports import Commitment, PlanningSnapshot


def to_instance(snapshot: PlanningSnapshot, horizon_s: float) -> ProblemInstance:
    """The scheduling instance of ``snapshot``, with horizon ``horizon_s``.

    The commitments become the committed calendar of the instance, and the new requests are the
    ones to plan. Each request keeps the release it has in the snapshot.
    """
    requests = (
        *(_request(c.request) for c in snapshot.commitments),
        *(_request(r) for r in snapshot.new_requests),
    )
    return ProblemInstance(
        network=_network(snapshot.constellation),
        requests=requests,
        horizon=horizon_s,
        plan_release=dict(snapshot.plan_arrival_s),
        committed=_committed(snapshot.commitments),
        name=f"epoch-{snapshot.epoch.index}",
    )


def _network(constellation: Constellation) -> Network:
    planes = tuple(
        Plane(
            plane.id,
            tuple(_satellite(s) for s in plane.satellites),
            plane.com,
        )
        for plane in constellation.planes
    )
    ground = constellation.ground_station.id
    arcs = tuple(arc for link in constellation.links for arc in _arcs(link, ground))
    return Network(planes, GroundStation(ground), arcs)


def _satellite(sat: SimSatellite) -> Satellite:
    return Satellite(
        id=sat.id,
        plmm_capacity=sat.plmm_capacity_gb,
        hpc_rate=sat.hpc_rate_gbps,
        hpc_windows=_window_set(sat.hpc_windows),
    )


def _arcs(link: Link, ground: NodeId) -> tuple[Arc, ...]:
    """The arcs of a link the scheduler accepts: both ways between satellites, and only the
    one towards the ground station."""
    directions = ((link.a, link.b), (link.b, link.a))
    return tuple(
        Arc(
            source=source,
            target=target,
            capacity=link.capacity_gbps,
            latency=link.latency_s,
            availability=_availability(link.availability),
        )
        for source, target in directions
        if source != ground
    )


def _availability(
    availability: SimAlwaysAvailable | SimWindowedAvailability,
) -> Availability:
    if isinstance(availability, SimWindowedAvailability):
        return WindowedAvailability(_window_set(availability.windows))
    return AlwaysAvailable()


def _window_set(windows: SimWindowSet) -> WindowSet:
    return WindowSet(TimeWindow(w.start, w.end) for w in windows)


def _request(request: RequestSpec) -> Request:
    return Request(
        id=request.id,
        priority=Priority[request.priority.name],
        origin=request.origin,
        release=request.release_s,
        deadline=request.deadline_s,
        raw_size=request.raw_size_gb,
        tasks=tuple(Task(t.execution_s, t.output_size_gb) for t in request.tasks),
    )


def _committed(commitments: tuple[Commitment, ...]) -> Schedule:
    return Schedule(
        executions=tuple(_execution(t) for c in commitments for t in c.tasks),
        transfers=tuple(_transfer(t) for c in commitments for t in c.transfers),
    )


def _execution(task: PlannedTask) -> TaskExecution:
    return TaskExecution(
        request_id=task.request_id,
        task_index=task.task_index,
        satellite=task.satellite,
        start=task.start_s,
        end=task.end_s,
    )


def _transfer(transfer: PlannedTransfer) -> Transfer:
    return Transfer(
        request_id=transfer.request_id,
        data_index=transfer.data_index,
        source=transfer.source,
        target=transfer.target,
        start=transfer.start_s,
        end=transfer.end_s,
    )
