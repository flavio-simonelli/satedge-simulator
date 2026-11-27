"""Availability: when something can be used, written as always, periodically, or in windows.

The HPC of a satellite and the links of the topology both have an availability, so both use the
types of this module.
"""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

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

    @model_validator(mode="after")
    def _ordered(self) -> WindowDoc:
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        return self


class AlwaysDoc(Document):
    """Available at every instant."""

    kind: Literal[AvailabilityKind.ALWAYS]


class PeriodicDoc(Document):
    """Available once every ``period_s``, for ``duration_s``, the first time from ``first_start_s``."""

    kind: Literal[AvailabilityKind.PERIODIC]
    first_start_s: float = Field(default=0, ge=0)
    period_s: float = Field(gt=0)
    duration_s: float = Field(gt=0)

    @model_validator(mode="after")
    def _duration_shorter_than_period(self) -> PeriodicDoc:
        if self.duration_s >= self.period_s:
            raise ValueError("duration_s must be shorter than period_s")
        return self


class WindowsDoc(Document):
    """Available in each of the listed windows, which are sorted and do not overlap."""

    kind: Literal[AvailabilityKind.WINDOWS]
    windows: list[WindowDoc] = Field(min_length=1)

    @field_validator("windows")
    @classmethod
    def _sorted_and_disjoint(cls, value: list[WindowDoc]) -> list[WindowDoc]:
        for before, after in pairwise(value):
            if after.start_s < before.end_s:
                raise ValueError(
                    "windows must be sorted by start_s and must not overlap"
                )
        return value


AvailabilityDoc = Annotated[
    AlwaysDoc | PeriodicDoc | WindowsDoc, Field(discriminator="kind")
]
