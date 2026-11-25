"""Contact plan of kind ``windows``: every window of every link, with its start and end."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.io.base import Document, check_schema_version, read_document
from satedge_simulator.io.contact_plan.table import ContactPlan


class WindowDoc(Document):
    """A window of time, in seconds."""

    start_s: float
    end_s: float


class LinkWindowsDoc(Document):
    """The visibility windows between two nodes."""

    a: str
    b: str
    windows: list[WindowDoc] = Field(default_factory=list)


class ExplicitContactPlanDoc(Document):
    """A contact plan file of kind ``windows``."""

    schema_version: str
    kind: str = "windows"
    links: list[LinkWindowsDoc] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


def read_explicit(path: Path, horizon_s: float | None) -> ContactPlan:
    """The contact plan in ``path``, whose windows are written one by one.

    The horizon is not needed: the windows are the ones of the file.
    """
    del horizon_s
    document = read_document(path, ExplicitContactPlanDoc)
    return ContactPlan(
        {
            (link.a, link.b): WindowSet(
                Window(w.start_s, w.end_s) for w in link.windows
            )
            for link in document.links
        }
    )
