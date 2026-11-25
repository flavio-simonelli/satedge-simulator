"""Runtime of a satellite: its HPC, its PLMM and the closing of its computing windows."""

from __future__ import annotations

import simpy

from satedge_simulator.domain.intervals import Window
from satedge_simulator.domain.topology import Satellite
from satedge_simulator.runtime.plmm import Plmm


class SatelliteRuntime:
    """A satellite during the simulation.

    The HPC is a resource of capacity one: a task holds it from its start to its end. The PLMM is
    the memory container of the satellite. The description (windows, capacities, rate) is the
    static one of the domain.
    """

    def __init__(
        self, env: simpy.Environment, satellite: Satellite, tolerance_s: float
    ) -> None:
        self.env = env
        self.satellite = satellite
        self.hpc = simpy.Resource(env, capacity=1)
        self.plmm = Plmm(env, satellite.plmm_capacity_gb)
        self._tolerance_s = tolerance_s
        self._closings: dict[Window, simpy.Event] = {}

    @property
    def node_id(self) -> str:
        return self.satellite.id

    def window_closing(self) -> simpy.Event | None:
        """The event that fires when the computing window open now closes, tolerance included.

        The event is created the first time a window is asked for and then shared, so all the
        executions in the same window wait for the same event.

        Returns:
            ``None`` if no computing window is open now.
        """
        now = self.env.now
        window = self.satellite.hpc_windows.containing(now, self._tolerance_s)
        if window is None:
            return None
        if window not in self._closings:
            closes_at = window.end + self._tolerance_s
            self._closings[window] = self.env.timeout(closes_at - now)
        return self._closings[window]
