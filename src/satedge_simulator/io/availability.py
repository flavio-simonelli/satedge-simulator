"""Availability: when something can be used, written as always, periodically, or in windows.

The HPC of a satellite and the links of the topology both have an availability, so both use the
types of this module.
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
    """One window of availability, in seconds."""

    start_s: float = Field(ge=0)
    end_s: float


class AlwaysDoc(Document):
    """Available at every instant."""

    kind: Literal[AvailabilityKind.ALWAYS]


class PeriodicDoc(Document):
    """Available once every ``period_s``, for ``duration_s``, the first time from ``first_start_s``."""

    kind: Literal[AvailabilityKind.PERIODIC]
    first_start_s: float = Field(default=0, ge=0)
    period_s: float = Field(gt=0)
    duration_s: float = Field(gt=0)


class WindowsDoc(Document):
    """Available in each of the listed windows, which are sorted and do not overlap."""

    kind: Literal[AvailabilityKind.WINDOWS]
    windows: list[WindowDoc] = Field(min_length=1)


AvailabilityDoc = Annotated[
    AlwaysDoc | PeriodicDoc | WindowsDoc, Field(discriminator="kind")
]
