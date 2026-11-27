"""Availability: the windows of an availability document, turned into the domain's windows.

A periodic availability is expanded here, up to a horizon: the domain holds the windows, not the
rule that generated them.
"""

from __future__ import annotations

import math

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import DomainError
from satedge_simulator.io.availability import PeriodicDoc, WindowsDoc


def periodic_windows(doc: PeriodicDoc, horizon_s: float) -> WindowSet:
    """The windows ``[first + k·period, first + k·period + duration]`` that start before the horizon.

    Raises:
        DomainError: If the duration is not shorter than the period, so that two windows
            would overlap.
    """
    if doc.duration_s >= doc.period_s:
        raise DomainError(
            f"periodic availability: duration_s {doc.duration_s} must be shorter than "
            f"period_s {doc.period_s}"
        )
    count = max(0, math.ceil((horizon_s - doc.first_start_s) / doc.period_s))
    return WindowSet(
        tuple(
            Window(start, start + doc.duration_s)
            for start in (doc.first_start_s + k * doc.period_s for k in range(count))
        )
    )


def explicit_windows(doc: WindowsDoc) -> WindowSet:
    """The windows listed in the document, in time order."""
    return WindowSet(
        tuple(
            Window(w.start_s, w.end_s)
            for w in sorted(doc.windows, key=lambda w: w.start_s)
        )
    )
