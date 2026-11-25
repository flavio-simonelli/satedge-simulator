"""The ledger of the data: the instant each data item is complete on each node."""

from __future__ import annotations

from dataclasses import dataclass

import simpy

from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import StateError


@dataclass(frozen=True, slots=True)
class DataKey:
    """A data item on a node: the raw data or the output of a task, of one request.

    Attributes:
        request_id: Request the data belongs to.
        data_index: 0 for the raw data, ``k`` for the output of task ``k - 1``.
        node: Node that holds the data.
    """

    request_id: str
    data_index: int
    node: NodeId


class DataLedger:
    """For each data item, an event that fires when the item is complete on its node.

    Waiting on the event is how an action waits for its input: no action looks at the state of
    the others at a given instant, so the order of simultaneous events does not matter.
    """

    def __init__(self, env: simpy.Environment) -> None:
        self._env = env
        self._complete: dict[DataKey, simpy.Event] = {}

    def complete_event(self, key: DataKey) -> simpy.Event:
        """The event that fires when the data item is complete on its node."""
        if key not in self._complete:
            self._complete[key] = self._env.event()
        return self._complete[key]

    def mark_complete(self, key: DataKey) -> None:
        """Record that the data item is complete now.

        Raises:
            StateError: If the item was already complete, which means it was produced twice.
        """
        event = self.complete_event(key)
        if event.triggered:
            raise StateError(f"il dato {key} è stato completato due volte")
        event.succeed()

    def is_complete(self, key: DataKey) -> bool:
        """Whether the data item is complete on its node."""
        return key in self._complete and self._complete[key].triggered
