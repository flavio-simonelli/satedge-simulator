"""Propagation of the plan: the earliest instant at which the plan reaches each satellite.

The plan is a list of commands, so it occupies no link capacity: it costs only the propagation
latency of each link. It leaves the ground station when it is ready, waits at a node for a link to
open when it must, and is relayed by the satellites. The search is Dijkstra's algorithm with time:
arriving earlier at a node never makes the rest of the route later, so the first arrival recorded
for a node is the earliest one.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Mapping

from satedge_simulator.domain.topology import (
    Constellation,
    Link,
    NodeId,
    WindowedAvailability,
)
from satedge_simulator.errors import ScenarioError


def plan_arrival_times(
    constellation: Constellation, ready_at_s: float
) -> Mapping[NodeId, float]:
    """Earliest instant, in seconds, at which the plan reaches each satellite.

    Args:
        constellation: The network the plan travels through.
        ready_at_s: Instant the plan is ready on the ground station.

    Returns:
        A mapping from each satellite to its arrival instant. A satellite the plan cannot reach
        maps to ``math.inf``.

    Raises:
        ScenarioError: If ``ready_at_s`` is not finite and non-negative.
    """
    if not (math.isfinite(ready_at_s) and ready_at_s >= 0):
        raise ScenarioError(
            f"plan ready instant must be finite and >= 0, got {ready_at_s}"
        )
    ground = constellation.ground_station.id
    incident = _incident_links(constellation)
    arrival: dict[NodeId, float] = {node: math.inf for node in _nodes(constellation)}
    arrival[ground] = ready_at_s
    queue: list[tuple[float, NodeId]] = [(ready_at_s, ground)]
    while queue:
        time, node = heapq.heappop(queue)
        if time > arrival[node]:
            continue  # a later entry for a node that was already reached earlier
        for link in incident.get(node, ()):
            neighbour = link.b if link.a == node else link.a
            reached = _traverse(link, time)
            if reached is not None and reached < arrival[neighbour]:
                arrival[neighbour] = reached
                heapq.heappush(queue, (reached, neighbour))
    return {s.id: arrival[s.id] for s in constellation.satellites}


def _traverse(link: Link, at_s: float) -> float | None:
    """Arrival at the far end of ``link`` for a plan that is at the near end at ``at_s``.

    The plan leaves at the first instant the link is open for the whole propagation latency, so
    that it arrives before the link closes. On an always available link it leaves at once.
    """
    if not isinstance(link.availability, WindowedAvailability):
        return at_s + link.latency_s
    departure = link.availability.windows.earliest_fit(at_s, link.latency_s)
    return None if departure is None else departure + link.latency_s


def _incident_links(constellation: Constellation) -> dict[NodeId, list[Link]]:
    incident: dict[NodeId, list[Link]] = {}
    for link in constellation.links:
        incident.setdefault(link.a, []).append(link)
        incident.setdefault(link.b, []).append(link)
    return incident


def _nodes(constellation: Constellation) -> list[NodeId]:
    return [*(s.id for s in constellation.satellites), constellation.ground_station.id]
