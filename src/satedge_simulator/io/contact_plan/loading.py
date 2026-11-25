"""Reading a contact plan file: its kind chooses the reader (Strategy)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, field_validator

from satedge_simulator.errors import DocumentError, ScenarioError
from satedge_simulator.io.base import check_schema_version, read_document
from satedge_simulator.io.contact_plan.explicit import read_explicit
from satedge_simulator.io.contact_plan.periodic import read_periodic
from satedge_simulator.io.contact_plan.table import ContactPlan


class ContactPlanKind(StrEnum):
    """How a contact plan file gives its windows."""

    WINDOWS = "windows"
    PERIODIC = "periodic"


Reader = Callable[[Path, float | None], ContactPlan]
"""Reads a contact plan of one kind, given the end of the simulation."""

READERS: Mapping[ContactPlanKind, Reader] = MappingProxyType(
    {ContactPlanKind.WINDOWS: read_explicit, ContactPlanKind.PERIODIC: read_periodic}
)
"""The reader of each kind. A new kind is a new reader and a new entry."""


class _Header(BaseModel):
    """The fields every kind has, read first to choose the reader."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str
    kind: ContactPlanKind = ContactPlanKind.WINDOWS

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


def load_contact_plan(path: str | Path, horizon_s: float | None = None) -> ContactPlan:
    """Read the contact plan in ``path``, of any kind.

    Args:
        path: The contact plan file.
        horizon_s: The end of the simulation. A periodic contact plan generates its windows
            while they open before it; the other kinds do not need it.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema of its kind, or
            if its windows are not valid. The message names the file.
    """
    file = Path(path)
    header = read_document(file, _Header)
    try:
        return READERS[header.kind](file, horizon_s)
    except DocumentError:
        raise
    except ScenarioError as error:
        raise DocumentError(f"{file}: {error}") from error
