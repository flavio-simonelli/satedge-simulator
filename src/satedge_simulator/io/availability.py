"""Availability: how a file writes when something can be used.

An availability has one of three forms, and its ``kind`` field says which one. The topology file
uses it for the links, and its single windows for the HPCs whose windows are listed. The values
are not checked here: whether they are meaningful is for the code that builds the domain.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from satedge_simulator.io.base import Document


class AvailabilityKind(StrEnum):
    """How an availability is written."""

    ALWAYS = "always"
    PERIODIC = "periodic"
    WINDOWS = "windows"


class WindowDoc(Document):
    """One window of time.

    Attributes:
        start_s: Instant the window opens, in seconds.
        end_s: Instant the window closes, in seconds.
    """

    start_s: float
    end_s: float


class AlwaysDoc(Document):
    """Available at every instant.

    Attributes:
        kind: Always ``always``.
    """

    kind: Literal[AvailabilityKind.ALWAYS]


class PeriodicDoc(Document):
    """Available in one window in each period.

    Attributes:
        kind: Always ``periodic``.
        first_start_s: Instant the first window opens, in seconds. It may be left out: it is
            then 0.
        period_s: Time between the openings of two consecutive windows, in seconds.
        duration_s: Length of each window, in seconds.
    """

    kind: Literal[AvailabilityKind.PERIODIC]
    first_start_s: float = 0
    period_s: float
    duration_s: float


class WindowsDoc(Document):
    """Available in the listed windows.

    Attributes:
        kind: Always ``windows``.
        windows: The windows, as the file lists them.
    """

    kind: Literal[AvailabilityKind.WINDOWS]
    windows: list[WindowDoc]


AvailabilityDoc = Annotated[
    AlwaysDoc | PeriodicDoc | WindowsDoc, Field(discriminator="kind")
]
"""An availability of any of the three forms. Its ``kind`` field says which one."""
