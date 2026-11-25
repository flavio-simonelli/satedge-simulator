"""Runtime of a satellite: its HPC, its PLMM and the closing of its computing windows."""

from __future__ import annotations

import simpy

from satedge_simulator.domain.topology import Satellite
from satedge_simulator.runtime.plmm import Plmm
from satedge_simulator.runtime.windows import WindowClosings


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
        self._closings = WindowClosings(env, satellite.hpc_windows, tolerance_s)

    @property
    def node_id(self) -> str:
        return self.satellite.id

    def window_closing(self) -> simpy.Event | None:
        """The closing of the computing window open now, or ``None`` if none is open.

        All the executions in the same window share the same event.
        """
        return self._closings.closing()
