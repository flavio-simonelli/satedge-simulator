"""The event log: every notification, one JSON object per line."""

from __future__ import annotations

import dataclasses
import json
from typing import TextIO

from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import Notification


class JsonlEventLog:
    """Writes each notification of a bus as a line ``{"type": ..., "time": ..., ...}``.

    The stream belongs to the caller, who opens and closes it.
    """

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def attach(self, bus: EventBus) -> None:
        """Start writing the notifications published on ``bus``."""
        bus.subscribe(Notification, self.write)

    def write(self, notification: Notification) -> None:
        record = {
            "type": type(notification).__name__,
            **dataclasses.asdict(notification),
        }
        self._stream.write(json.dumps(record) + "\n")
