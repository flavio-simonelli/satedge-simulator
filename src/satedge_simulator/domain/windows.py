"""Windows of time: the computing windows of the HPCs and the visibility windows of the links."""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from satedge_simulator.domain.quantities import Duration, Time
from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True)
class Window:
    """A closed window of time ``[start, end]``.

    Attributes:
        start: Opening instant.
        end: Closing instant, after ``start``.
    """

    start: Time
    end: Time

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise DomainError(
                f"window [{self.start.seconds}, {self.end.seconds}]: "
                "the end must be after the start"
            )

    @property
    def duration(self) -> Duration:
        """Length of the window."""
        return self.end - self.start

    def contains(self, instant: Time, eps: Duration = Duration.ZERO) -> bool:
        """Whether ``instant`` lies in the window, up to ``eps`` on each side."""
        return self.covers(instant, instant, eps)

    def covers(self, start: Time, end: Time, eps: Duration = Duration.ZERO) -> bool:
        """Whether the span ``[start, end]`` lies in the window, up to ``eps`` on each side."""
        return (
            self.start.seconds - eps.seconds <= start.seconds
            and end.seconds <= self.end.seconds + eps.seconds
        )


@dataclass(frozen=True, slots=True)
class WindowSet:
    """An immutable set of windows, in time order and strictly disjoint.

    Two windows that only touch are rejected: they stand for one longer window.

    Attributes:
        windows: The windows, in time order. Each one starts after the previous one ends.
    """

    windows: tuple[Window, ...] = ()

    def __post_init__(self) -> None:
        # A list is accepted too: it is stored as a tuple, so the set cannot be changed later and
        # compares equal to one built from a tuple. The class is frozen, so a plain assignment
        # would raise: only object.__setattr__ can replace the field here.
        windows = tuple(self.windows)
        object.__setattr__(self, "windows", windows)
        for previous, current in itertools.pairwise(windows):
            if current.start <= previous.end:
                raise DomainError(
                    f"windows [{previous.start.seconds}, {previous.end.seconds}] and "
                    f"[{current.start.seconds}, {current.end.seconds}] "
                    "must be in time order, and must neither overlap nor touch"
                )
