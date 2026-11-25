"""Guarded waits: wait for an event, but no longer than a tolerance."""

from __future__ import annotations

from collections.abc import Generator

import simpy
from simpy.resources.resource import Request


def guarded_wait(
    env: simpy.Environment, event: simpy.Event, tolerance_s: float
) -> Generator[simpy.Event, object, bool]:
    """Wait for ``event`` for at most ``tolerance_s`` seconds.

    Returns ``True`` if the event happened in time, ``False`` if the tolerance expired first. The
    outcome does not depend on the order in which simultaneous events are processed: an event that
    fires at the instant of the wait counts as in time.
    """
    timer = env.timeout(tolerance_s)
    yield simpy.AnyOf(env, [event, timer])
    return event.triggered


def guarded_request(
    env: simpy.Environment, request: Request, tolerance_s: float
) -> Generator[simpy.Event, object, bool]:
    """Wait for a resource request within the tolerance; cancel it if it is not granted."""
    granted = yield from guarded_wait(env, request, tolerance_s)
    if not granted:
        request.cancel()
    return granted
