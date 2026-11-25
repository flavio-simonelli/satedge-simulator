"""Contact plan: the visibility windows of the links that are not always available.

:class:`ContactPlan` is the in-memory table. The file has three kinds, chosen by its ``kind``:

- ``windows`` (the default): every window, with its start and end;
- ``periodic``: for each link the first opening, the period and the duration, the windows
  generated up to the horizon of the simulation, as long as it is;
- ``orekit``: the windows computed by isl-windows-visibility with Orekit, read from its JSON
  result, with the nodes renamed as the topology names them.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class ContactPlanKind(StrEnum):
    """How a contact plan file gives its windows."""

    WINDOWS = "windows"
    PERIODIC = "periodic"
    OREKIT = "orekit"


class ContactPlanHeader(BaseModel):
    """The fields every kind of contact plan has, read to choose the schema of the rest."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str
    kind: ContactPlanKind = ContactPlanKind.WINDOWS

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


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
    """A contact plan file of kind ``windows``."""

    schema_version: str
    kind: ContactPlanKind = ContactPlanKind.WINDOWS
    links: list[LinkWindowsDoc] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


class PeriodicLinkDoc(Document):
    """The windows of a link that opens every ``period_s`` for ``duration_s``."""

    a: str
    b: str
    first_start_s: float
    period_s: float
    duration_s: float


class PeriodicContactPlanDoc(Document):
    """A contact plan file of kind ``periodic``."""

    schema_version: str
    kind: ContactPlanKind
    links: list[PeriodicLinkDoc] = Field(default_factory=list)


class OrekitContactPlanDoc(Document):
    """A contact plan file of kind ``orekit``: the result to read, and the names to change.

    Attributes:
        source: The JSON result of isl-windows-visibility, relative to this file.
        names: The name in the topology of each node the result names differently.
    """

    schema_version: str
    kind: ContactPlanKind
    source: str
    names: dict[str, str] = Field(default_factory=dict)


class _OrekitWindow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_offset_s: float
    end_offset_s: float


class _OrekitLink(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_a: str
    node_b: str
    windows: list[_OrekitWindow] = Field(default_factory=list)


class _OrekitResult(BaseModel):
    """The part of the result of isl-windows-visibility the simulator reads."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str
    links: list[_OrekitLink]

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


def load_contact_plan(path: str | Path, horizon_s: float | None = None) -> ContactPlan:
    """Read the contact plan in ``path``, of any kind.

    Args:
        path: The contact plan file.
        horizon_s: The end of the simulation: the periodic windows are generated while they
            start before it. Needed only by a periodic contact plan.

    Raises:
        DocumentError: If a file cannot be read or does not match the schema of its kind, or if
            its windows are not valid. The message names the file.
    """
    header = read_document(path, ContactPlanHeader)
    try:
        if header.kind is ContactPlanKind.PERIODIC:
            if horizon_s is None:
                raise ScenarioError(
                    "un contact plan periodico richiede l'orizzonte della simulazione"
                )
            return _periodic(read_document(path, PeriodicContactPlanDoc), horizon_s)
        if header.kind is ContactPlanKind.OREKIT:
            return _orekit(path, read_document(path, OrekitContactPlanDoc))
        return _explicit(read_document(path, ContactPlanDoc))
    except ScenarioError as error:
        if isinstance(error, DocumentError):
            raise
        raise DocumentError(f"{path}: {error}") from error


def _explicit(document: ContactPlanDoc) -> ContactPlan:
    return ContactPlan(
        {
            (link.a, link.b): WindowSet(
                Window(w.start_s, w.end_s) for w in link.windows
            )
            for link in document.links
        }
    )


def _periodic(document: PeriodicContactPlanDoc, horizon_s: float) -> ContactPlan:
    return ContactPlan(
        {(link.a, link.b): periodic_windows(link, horizon_s) for link in document.links}
    )


def periodic_windows(link: PeriodicLinkDoc, horizon_s: float) -> WindowSet:
    """The windows ``[first + k·period, first + k·period + duration]`` that start before the
    horizon.

    Raises:
        ScenarioError: If the first start is negative, or the duration is not shorter than the
            period: two windows of the same link would overlap or touch.
    """
    what = f"link {link.a}-{link.b}"
    if not (math.isfinite(link.first_start_s) and link.first_start_s >= 0):
        raise ScenarioError(f"{what}: la prima apertura deve essere >= 0")
    if not 0 < link.duration_s < link.period_s:
        raise ScenarioError(f"{what}: serve 0 < durata < periodo")
    windows = []
    start = link.first_start_s
    while start < horizon_s:
        windows.append(Window(start, start + link.duration_s))
        start += link.period_s
    return WindowSet(windows)


def _orekit(path: str | Path, document: OrekitContactPlanDoc) -> ContactPlan:
    result = read_document(Path(path).parent / document.source, _OrekitResult)

    def name(node: str) -> str:
        return document.names.get(node, node)

    return ContactPlan(
        {
            (name(link.node_a), name(link.node_b)): WindowSet(
                Window(w.start_offset_s, w.end_offset_s) for w in link.windows
            )
            for link in result.links
        }
    )
