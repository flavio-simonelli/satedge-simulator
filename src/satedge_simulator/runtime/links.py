"""Runtime of one direction of a link: its channel and the closing of its visibility windows."""

from __future__ import annotations

import simpy

from satedge_simulator.domain.topology import Link, NodeId, WindowedAvailability
from satedge_simulator.errors import StateError
from satedge_simulator.runtime.windows import WindowClosings


class LinkRuntime:
    """One direction of a link during the simulation.

    The channel is a resource of capacity one: a transmission holds it from its start to the end
    of the transmission on the sender. The two directions of a link are independent, so each has
    its own ``LinkRuntime``. Capacity, latency and windows are the static ones of the domain.
    """

    def __init__(
        self,
        env: simpy.Environment,
        link: Link,
        source: NodeId,
        target: NodeId,
        tolerance_s: float,
    ) -> None:
        if not link.connects(source, target):
            raise StateError(f"link {link.name} does not join {source} and {target}")
        self.env = env
        self.link = link
        self.source = source
        self.target = target
        self.channel = simpy.Resource(env, capacity=1)
        availability = link.availability
        self._closings = (
            WindowClosings(env, availability.windows, tolerance_s)
            if isinstance(availability, WindowedAvailability)
            else None
        )
        self._never = env.event()

    def window_closing(self) -> simpy.Event | None:
        """The closing of the visibility window open now, or ``None`` if the link is not visible.

        A link that is always available never closes: its event never fires.
        """
        if self._closings is None:
            return self._never
        return self._closings.closing()
