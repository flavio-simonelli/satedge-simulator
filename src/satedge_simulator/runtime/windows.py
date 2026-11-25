"""The closing of the windows of a resource, as SimPy events."""

from __future__ import annotations

import simpy

from satedge_simulator.domain.intervals import Window, WindowSet


class WindowClosings:
    """For each window, the event that fires when it closes, tolerance included.

    An action races the closing of the window it runs in (a watchdog): any delay that pushes it
    past the window stops it. The event of a window is created the first time it is asked for and
    then shared by all the actions in that window.
    """

    def __init__(
        self, env: simpy.Environment, windows: WindowSet, tolerance_s: float
    ) -> None:
        self._env = env
        self._windows = windows
        self._tolerance_s = tolerance_s
        self._closings: dict[Window, simpy.Event] = {}

    def closing(self) -> simpy.Event | None:
        """The closing of the window open now, or ``None`` if no window is open now."""
        now = self._env.now
        window = self._windows.containing(now, self._tolerance_s)
        if window is None:
            return None
        if window not in self._closings:
            closes_at = window.end + self._tolerance_s
            self._closings[window] = self._env.timeout(closes_at - now)
        return self._closings[window]
