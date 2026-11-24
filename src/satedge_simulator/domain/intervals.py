"""Windows of time: the computing windows of the HPCs and the visibility windows of the links."""

from __future__ import annotations

import bisect
import itertools
import math
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from satedge_simulator.errors import ScenarioError


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
            raise ScenarioError(
                f"window [{self.start}, {self.end}]: bounds must be finite"
            )
        if self.start < 0 or self.end <= self.start:
            raise ScenarioError(
                f"window [{self.start}, {self.end}]: needs 0 <= start < end"
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

    def clipped(self, until: float) -> float:
        """Duration of the part of the window before ``until``."""
        return max(0.0, min(self.end, until) - self.start)


class WindowSet:
    """An immutable set of windows, sorted and strictly disjoint.

    Two windows that only touch are rejected: they stand for one longer window.
    """

    __slots__ = ("_starts", "_windows")

    def __init__(self, windows: Iterable[Window] = ()) -> None:
        ordered = tuple(sorted(windows, key=lambda w: w.start))
        for previous, current in itertools.pairwise(ordered):
            if current.start <= previous.end:
                raise ScenarioError(
                    f"windows [{previous.start}, {previous.end}] and "
                    f"[{current.start}, {current.end}] overlap or touch"
                )
        self._windows = ordered
        self._starts = tuple(w.start for w in ordered)

    @property
    def windows(self) -> tuple[Window, ...]:
        """The windows, in time order."""
        return self._windows

    def __iter__(self) -> Iterator[Window]:
        return iter(self._windows)

    def __len__(self) -> int:
        return len(self._windows)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WindowSet):
            return NotImplemented
        return self._windows == other._windows

    def __hash__(self) -> int:
        return hash(self._windows)

    def __repr__(self) -> str:
        return f"WindowSet({list(self._windows)!r})"

    def containing(self, instant: float, eps: float = 0.0) -> Window | None:
        """The window that contains ``instant`` up to ``eps``, if any."""
        k = bisect.bisect_right(self._starts, instant + eps) - 1
        if k >= 0 and self._windows[k].contains(instant, eps):
            return self._windows[k]
        return None

    def first_ending_after(self, instant: float) -> int:
        """Index of the first window that ends after ``instant`` (``len`` if none)."""
        lo, hi = 0, len(self._windows)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._windows[mid].end <= instant:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def earliest_fit(self, instant: float, length: float) -> float | None:
        """Earliest start ``>= instant`` of a span of ``length`` inside one window, if any."""
        for window in self._windows[self.first_ending_after(instant) :]:
            start = max(instant, window.start)
            if start + length <= window.end:
                return start
        return None

    def total_duration(self, until: float = math.inf) -> float:
        """Total open time of the windows before ``until``."""
        return sum(w.clipped(until) for w in self._windows)
