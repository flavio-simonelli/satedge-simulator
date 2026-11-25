"""The PLMM of a satellite: its memory, with the occupation of each data item."""

from __future__ import annotations

from collections.abc import Generator

import simpy
from simpy.resources.container import ContainerPut

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import StateError
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import PlmmChanged
from satedge_simulator.runtime.ledger import DataKey
from satedge_simulator.runtime.timing import guarded_wait


class Plmm:
    """The memory of a satellite, as a container, plus the size each data item occupies.

    The container tells how much memory is free; the occupations tell which item uses it, so that
    the memory of a failed request can be freed and the occupation can be measured. Every
    change of the occupied memory is published on ``bus``.
    """

    def __init__(
        self,
        env: simpy.Environment,
        capacity_gb: float,
        satellite: NodeId = "",
        bus: EventBus | None = None,
    ) -> None:
        self._env = env
        self._container = simpy.Container(env, capacity=capacity_gb)
        self._occupied: dict[DataKey, float] = {}
        self._satellite = satellite
        self._bus = bus or EventBus()

    @property
    def level_gb(self) -> float:
        """Memory currently occupied, in Gb."""
        return self._container.level

    def occupied_gb(self, key: DataKey) -> float:
        """Memory occupied by ``key``, in Gb; zero if the item is not stored."""
        return self._occupied.get(key, 0.0)

    def reserve(
        self, env: simpy.Environment, key: DataKey, size_gb: float, tolerance_s: float
    ) -> Generator[simpy.Event, object, bool]:
        """Store ``key`` of ``size_gb``, waiting at most ``tolerance_s`` for free memory.

        Returns:
            ``True`` if the item is stored, ``False`` if the memory did not free up in time; in
            that case nothing is stored and the pending request is cancelled. If the caller is
            interrupted while waiting, the pending request is cancelled too, or recorded if it was
            granted at that very instant, so that ``release`` frees it.

        Raises:
            StateError: If the item is already stored.
        """
        if key in self._occupied:
            raise StateError(f"data {key} already stored in the PLMM")
        put = self._container.put(size_gb)
        try:
            granted = yield from guarded_wait(env, put, tolerance_s)
        except simpy.Interrupt:
            self._abandon(key, put, size_gb)
            raise
        if not granted:
            put.cancel()
            return False
        self._store(key, size_gb)
        return True

    def _abandon(self, key: DataKey, put: ContainerPut, size_gb: float) -> None:
        """Undo a reservation whose waiter was interrupted."""
        if put.triggered:
            self._store(key, size_gb)
        else:
            put.cancel()

    def release(self, key: DataKey) -> None:
        """Free the memory of ``key``. Releasing an item that is not stored is a no-op."""
        size_gb = self._occupied.pop(key, None)
        if size_gb is not None:
            self._container.get(size_gb)  # the level drops at once
            self._publish(self._container.level)

    def _store(self, key: DataKey, size_gb: float) -> None:
        self._occupied[key] = size_gb
        self._publish(self._container.level)

    def _publish(self, level_gb: float) -> None:
        self._bus.publish(PlmmChanged(self._env.now, self._satellite, level_gb))

    def release_request(self, request_id: str) -> None:
        """Free the memory of every item of ``request_id``, as when the request fails."""
        for key in [k for k in self._occupied if k.request_id == request_id]:
            self.release(key)
