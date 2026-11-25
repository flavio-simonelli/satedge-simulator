"""Runtime of the network: the satellites and the two directions of every link."""

from __future__ import annotations

import simpy

from satedge_simulator.domain.topology import Constellation, NodeId
from satedge_simulator.errors import StateError
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.runtime.links import LinkRuntime
from satedge_simulator.runtime.satellite import SatelliteRuntime


class NetworkRuntime:
    """The constellation during the simulation: one runtime per satellite and per arc."""

    def __init__(
        self,
        env: simpy.Environment,
        constellation: Constellation,
        tolerance_s: float,
        bus: EventBus | None = None,
    ) -> None:
        self.constellation = constellation
        self._satellites = {
            s.id: SatelliteRuntime(env, s, tolerance_s, bus)
            for s in constellation.satellites
        }
        self._links: dict[tuple[NodeId, NodeId], LinkRuntime] = {}
        for link in constellation.links:
            for source, target in ((link.a, link.b), (link.b, link.a)):
                self._links[(source, target)] = LinkRuntime(
                    env, link, source, target, tolerance_s, bus
                )

    @property
    def satellites(self) -> tuple[SatelliteRuntime, ...]:
        return tuple(self._satellites.values())

    def satellite(self, node: NodeId) -> SatelliteRuntime:
        """The runtime of satellite ``node``.

        Raises:
            StateError: If ``node`` is not a satellite.
        """
        if node not in self._satellites:
            raise StateError(f"{node!r} is not a satellite")
        return self._satellites[node]

    def receiver(self, node: NodeId) -> SatelliteRuntime | None:
        """The satellite that stores what reaches ``node``; ``None`` for the ground station."""
        if node == self.constellation.ground_station.id:
            return None
        return self.satellite(node)

    def arc(self, source: NodeId, target: NodeId) -> LinkRuntime:
        """The direction ``source -> target`` of the link between them.

        Raises:
            StateError: If no link joins the two nodes.
        """
        if (source, target) not in self._links:
            raise StateError(f"no link joins {source} and {target}")
        return self._links[(source, target)]
