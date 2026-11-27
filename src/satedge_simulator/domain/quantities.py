"""Quantities of the domain: instants and lengths of time, sizes of data, and rates.

Each quantity is a value that cannot be invalid, and its unit is in the name of its field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar, overload

from satedge_simulator.errors import DomainError


@dataclass(frozen=True, slots=True, order=True)
class Time:
    """An instant of simulation, in seconds: finite and >= 0."""

    seconds: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise DomainError(f"time {self.seconds}: it must be finite and >= 0")

    def __add__(self, other: Duration) -> Time:
        return Time(self.seconds + other.seconds)

    @overload
    def __sub__(self, other: Time) -> Duration: ...

    @overload
    def __sub__(self, other: Duration) -> Time: ...

    def __sub__(self, other: Time | Duration) -> Duration | Time:
        """The time elapsed since an earlier instant, or the instant a duration before this one.

        Raises:
            DomainError: If ``other`` is an instant after this one, or a duration that reaches
                before the instant 0.
        """
        if isinstance(other, Time):
            if other > self:
                raise DomainError(
                    f"time {self.seconds} - time {other.seconds}: "
                    "the subtracted instant must not be after the other"
                )
            return Duration(self.seconds - other.seconds)
        if isinstance(other, Duration):
            if other.seconds > self.seconds:
                raise DomainError(
                    f"time {self.seconds} - duration {other.seconds}: "
                    "the result would be before the instant 0"
                )
            return Time(self.seconds - other.seconds)
        return NotImplemented


@dataclass(frozen=True, slots=True, order=True)
class Duration:
    """A length of time, in seconds: finite and >= 0.

    ``Duration.ZERO`` is the empty length of time.
    """

    ZERO: ClassVar[Duration]
    seconds: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise DomainError(f"duration {self.seconds}: it must be finite and >= 0")


Duration.ZERO = Duration(0.0)


@dataclass(frozen=True, slots=True, order=True)
class DataSize:
    """A size of data, in gigabits (Gb): finite and >= 0."""

    gigabits: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.gigabits) or self.gigabits < 0:
            raise DomainError(f"data size {self.gigabits}: it must be finite and >= 0")


@dataclass(frozen=True, slots=True, order=True)
class Rate:
    """A rate of transfer, in gigabits per second: finite and > 0."""

    gigabits_per_second: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.gigabits_per_second) or self.gigabits_per_second <= 0:
            raise DomainError(
                f"rate {self.gigabits_per_second}: it must be finite and > 0"
            )

    def transfer_time(self, size: DataSize) -> Duration:
        """The time needed to transfer ``size`` at this rate. It does not include latency."""
        return Duration(size.gigabits / self.gigabits_per_second)
