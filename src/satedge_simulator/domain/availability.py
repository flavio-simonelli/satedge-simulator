"""Availability: when something can be used, such as the HPC of a satellite or a link.

The simulation and the scheduler use :class:`Availability` only, so they need not know which kind
they are given. A new kind is a new class with its three methods: nothing else has to change.

An availability may never close, and a :class:`~satedge_simulator.domain.windows.Window` always
does. So the questions are about instants, not windows: when it next opens, and when it then
closes.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from typing import Protocol

from satedge_simulator.domain.quantities import Duration, Time
from satedge_simulator.domain.windows import Window, WindowSet
from satedge_simulator.errors import DomainError


class Availability(Protocol):
    """When something can be used."""

    def is_available(self, t: Time) -> bool:
        """Whether it can be used at ``t``. The instants a window opens and closes count."""
        ...

    def next_opening(self, t: Time) -> Time | None:
        """The first instant, from ``t`` on, at which it can be used.

        It is ``t`` itself if it can be used at ``t``, and ``None`` if it never can again.
        """
        ...

    def closing_after(self, t: Time) -> Time | None:
        """The instant it closes, for the first time from ``t`` on.

        If it can be used at ``t``, this is when it stops. Otherwise it is the end of the next
        window. ``None`` means that there is no such instant: either it never closes, or it
        never opens again. :meth:`next_opening` tells the two apart, since it is ``None`` only
        in the second case.
        """
        ...


@dataclass(frozen=True, slots=True)
class Always:
    """Available at every instant: it never closes."""

    def is_available(self, t: Time) -> bool:
        return True

    def next_opening(self, t: Time) -> Time | None:
        return t

    def closing_after(self, t: Time) -> Time | None:
        return None


@dataclass(frozen=True, slots=True)
class Periodic:
    """Available in the windows ``[first + k·period, first + k·period + duration]``, for every
    whole ``k`` from 0 on.

    Attributes:
        first_start: Instant the first window opens.
        period: Time between the openings of two consecutive windows.
        duration: Length of each window: more than zero, and shorter than ``period``, so that
            two windows neither overlap nor touch.
    """

    first_start: Time
    period: Duration
    duration: Duration

    def __post_init__(self) -> None:
        if not Duration.ZERO < self.duration < self.period:
            raise DomainError(
                f"periodic availability: it must hold 0 < duration < period, got duration "
                f"{self.duration.seconds} and period {self.period.seconds}"
            )

    def is_available(self, t: Time) -> bool:
        return self._current_or_next(t).contains(t)

    def next_opening(self, t: Time) -> Time | None:
        return max(t, self._current_or_next(t).start)

    def closing_after(self, t: Time) -> Time | None:
        return self._current_or_next(t).end

    def _current_or_next(self, t: Time) -> Window:
        """The first window that has not closed before ``t``."""
        elapsed = t.seconds - self.first_start.seconds
        index = max(0, math.floor(elapsed / self.period.seconds))
        window = self._window(index)
        return window if t <= window.end else self._window(index + 1)

    def _window(self, index: int) -> Window:
        start = Time(self.first_start.seconds + index * self.period.seconds)
        return Window(start, start + self.duration)


@dataclass(frozen=True, slots=True)
class Scheduled:
    """Available in the windows of a set, and never after the last one.

    Attributes:
        windows: The windows. With none, it is never available.
    """

    windows: WindowSet

    def is_available(self, t: Time) -> bool:
        window = self._current_or_next(t)
        return window is not None and window.contains(t)

    def next_opening(self, t: Time) -> Time | None:
        window = self._current_or_next(t)
        return None if window is None else max(t, window.start)

    def closing_after(self, t: Time) -> Time | None:
        window = self._current_or_next(t)
        return None if window is None else window.end

    def _current_or_next(self, t: Time) -> Window | None:
        """The first window that has not closed before ``t``, if there is one."""
        # A binary search, so that many windows cost little. It needs the ends in increasing
        # order, which WindowSet guarantees: its windows are in time order and do not overlap.
        windows = self.windows.windows
        index = bisect_left(windows, t, key=lambda w: w.end)
        return windows[index] if index < len(windows) else None
