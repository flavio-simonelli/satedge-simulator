"""Guarded waits: wait for an event, but no longer than a tolerance."""

from __future__ import annotations

from collections.abc import Generator

import simpy


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
