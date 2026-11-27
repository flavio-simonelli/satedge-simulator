"""Availability mapping: the availability documents, turned into the domain's availabilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import assert_never

from satedge_simulator.domain.availability import (
    Always,
    Availability,
    Periodic,
    Scheduled,
)
from satedge_simulator.domain.quantities import Duration, Time
from satedge_simulator.domain.windows import Window, WindowSet
from satedge_simulator.io.availability import (
    AlwaysDoc,
    AvailabilityDoc,
    PeriodicDoc,
    WindowDoc,
    WindowsDoc,
)


def periodic(first_start_s: float, period_s: float, duration_s: float) -> Periodic:
    """The periodic availability with these values, in seconds.

    Raises:
        DomainError: If a value breaks a rule of the domain.
    """
    return Periodic(Time(first_start_s), Duration(period_s), Duration(duration_s))


def scheduled(windows: Iterable[WindowDoc]) -> Scheduled:
    """The availability in the listed windows, which the file may list in any order.

    Raises:
        DomainError: If a window is not valid, or two windows overlap or touch.
    """
    ordered = sorted(windows, key=lambda w: w.start_s)
    return Scheduled(
        WindowSet(tuple(Window(Time(w.start_s), Time(w.end_s)) for w in ordered))
    )


def availability(doc: AvailabilityDoc) -> Availability:
    """The availability that ``doc`` describes.

    Raises:
        DomainError: If a value breaks a rule of the domain.
    """
    match doc:
        case AlwaysDoc():
            return Always()
        case PeriodicDoc():
            return periodic(doc.first_start_s, doc.period_s, doc.duration_s)
        case WindowsDoc():
            return scheduled(doc.windows)
        case _:
            assert_never(doc)
