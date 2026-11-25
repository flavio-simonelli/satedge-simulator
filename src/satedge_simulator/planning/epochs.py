"""Planning epochs: the instants at which the ground segment computes a plan.

An epoch starts ``lead_time_s`` before the opening of a contact between the ground station and a
communication satellite, so the plan is ready when the contact opens. Openings at the same
instant share one epoch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from satedge_simulator.domain.topology import Constellation, WindowedAvailability
from satedge_simulator.errors import ScenarioError


@dataclass(frozen=True, slots=True)
class Epoch:
    """One planning epoch.

    Attributes:
        index: Position of the epoch in the simulation, from 0.
        start_s: Instant the planning starts, in seconds.
        ready_s: Instant the plan is ready, which is the opening of the contact, in seconds.
    """

    index: int
    start_s: float
    ready_s: float

    @property
    def lead_time_s(self) -> float:
        """Seconds between the start of the planning and the readiness of the plan."""
        return self.ready_s - self.start_s


def contact_openings(constellation: Constellation) -> tuple[float, ...]:
    """Sorted instants at which a windowed link joins the ground station to a satellite."""
    ground = constellation.ground_station.id
    openings: set[float] = set()
    for link in constellation.links:
        if ground not in (link.a, link.b) or not isinstance(
            link.availability, WindowedAvailability
        ):
            continue
        openings.update(window.start for window in link.availability.windows)
    return tuple(sorted(openings))


def planning_epochs(
    constellation: Constellation, lead_time_s: float, end_s: float
) -> tuple[Epoch, ...]:
    """The epochs that start in ``[0, end_s)`` for a planning that needs ``lead_time_s``.

    An opening closer than ``lead_time_s`` to the beginning has no epoch: the plan could not be
    ready in time.

    Raises:
        ScenarioError: If the lead time or the end is not finite and positive.
    """
    _require_positive_finite(lead_time_s, "anticipo del calcolo")
    _require_positive_finite(end_s, "fine della simulazione")
    planned = [
        (opening - lead_time_s, opening)
        for opening in contact_openings(constellation)
        if 0.0 <= opening - lead_time_s < end_s
    ]
    return tuple(
        Epoch(index=k, start_s=start, ready_s=ready)
        for k, (start, ready) in enumerate(planned)
    )


def _require_positive_finite(value: float, what: str) -> None:
    if not (math.isfinite(value) and value > 0):
        raise ScenarioError(f"{what}: deve essere finito e > 0, invece è {value}")
