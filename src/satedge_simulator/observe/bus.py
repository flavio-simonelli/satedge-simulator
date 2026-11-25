"""The bus of the notifications: the runtime publishes, the subscribers listen."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar, cast

from satedge_simulator.observe.notifications import Notification

N = TypeVar("N", bound=Notification)


class EventBus:
    """Delivers each notification to the subscribers of its type, in subscription order.

    A subscriber of :class:`Notification` hears every notification, as the event log does. A
    bus without subscribers costs only the call: it is the default of every publisher.
    """

    def __init__(self) -> None:
        self._subscribers: defaultdict[
            type[Notification], list[Callable[[Any], None]]
        ] = defaultdict(list)

    def subscribe(self, kind: type[N], callback: Callable[[N], None]) -> None:
        """Call ``callback`` with every published notification of type ``kind``."""
        self._subscribers[kind].append(cast(Callable[[Any], None], callback))

    def publish(self, notification: Notification) -> None:
        """Deliver ``notification`` to the subscribers of its type, then to those of all."""
        for callback in self._subscribers.get(type(notification), ()):
            callback(notification)
        if type(notification) is not Notification:
            for callback in self._subscribers.get(Notification, ()):
                callback(notification)
