"""Windows of time: the computing windows of the HPCs and the visibility windows of the links."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True)
class Window:
    """A closed window of time ``[start, end]``, in seconds.

    Attributes:
        start: Opening instant (finite, >= 0).
        end: Closing instant (finite, > start).
    """

    start: float
    end: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.start) and math.isfinite(self.end)):
            raise DomainError(
                f"window [{self.start}, {self.end}]: the bounds must be finite"
            )
        if self.start < 0 or self.end <= self.start:
            raise DomainError(
                f"window [{self.start}, {self.end}]: it must hold 0 <= start < end"
            )

    @property
    def duration(self) -> float:
        """Length of the window in seconds."""
        return self.end - self.start

    def contains(self, instant: float, eps: float = 0.0) -> bool:
        """Whether ``instant`` lies in the window, up to ``eps`` on each side."""
        return self.start - eps <= instant <= self.end + eps

    def covers(self, start: float, end: float, eps: float = 0.0) -> bool:
        """Whether the span ``[start, end]`` lies in the window, up to ``eps`` on each side."""
        return self.start - eps <= start and end <= self.end + eps


@dataclass(frozen=True, slots=True)
class WindowSet:
    """An immutable set of windows, in time order and strictly disjoint.

    Two windows that only touch are rejected: they stand for one longer window.

    Attributes:
        windows: The windows, in time order. Each one starts after the previous one ends.
    """

    windows: tuple[Window, ...] = ()

    def __post_init__(self) -> None:
        windows = tuple(self.windows)
        object.__setattr__(self, "windows", windows)
        for previous, current in itertools.pairwise(windows):
            if current.start <= previous.end:
                raise DomainError(
                    f"windows [{previous.start}, {previous.end}] and "
                    f"[{current.start}, {current.end}] must be in time order, and must "
                    "neither overlap nor touch"
                )
