"""Contact plan: the visibility windows of the links that are not always available.

:class:`ContactPlan` is the in-memory table; the schema and :func:`load_contact_plan` read it
from its YAML file.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import Field, field_validator

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import DocumentError, ScenarioError
from satedge_simulator.io.base import Document, check_schema_version, read_document


class ContactPlan:
    """Visibility windows of node pairs, looked up regardless of the order of the pair."""

    __slots__ = ("_windows",)

    def __init__(self, windows: Mapping[tuple[NodeId, NodeId], WindowSet]) -> None:
        self._windows: dict[frozenset[NodeId], WindowSet] = {}
        for (a, b), window_set in windows.items():
            if a == b:
                raise ScenarioError(f"contact plan: {a} è in contatto con sé stesso")
            pair = frozenset((a, b))
            if pair in self._windows:
                raise ScenarioError(f"contact plan: {a}-{b} è dichiarato più volte")
            self._windows[pair] = window_set

    def windows_of(self, a: NodeId, b: NodeId) -> WindowSet:
        """Visibility windows between ``a`` and ``b``."""
        try:
            return self._windows[frozenset((a, b))]
        except KeyError:
            raise ScenarioError(
                f"il contact plan non ha finestre per {a}-{b}"
            ) from None


class WindowDoc(Document):
    """A window of time, in seconds."""

    start_s: float
    end_s: float


class LinkWindowsDoc(Document):
    """The visibility windows between two nodes."""

    a: str
    b: str
    windows: list[WindowDoc] = Field(default_factory=list)


class ContactPlanDoc(Document):
    """A contact plan file."""

    schema_version: str
    links: list[LinkWindowsDoc] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


def load_contact_plan(path: str | Path) -> ContactPlan:
    """Read the contact plan in ``path``.

    Raises:
        DocumentError: If the file cannot be read or does not match the schema, or if its
            windows are not valid. The message names the file.
    """
    document = read_document(path, ContactPlanDoc)
    try:
        return ContactPlan(
            {
                (link.a, link.b): WindowSet(
                    Window(w.start_s, w.end_s) for w in link.windows
                )
                for link in document.links
            }
        )
    except ScenarioError as error:
        raise DocumentError(f"{path}: {error}") from error
