"""Contact plan of kind ``periodic``: each link opens every period, for the same duration.

It is how the contacts of the case study are described (COM-COM once per orbital period for
about 10 min, COM-ground every half period for about 3 min), and it covers a run of any length.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.errors import ScenarioError
from satedge_simulator.io.base import Document, check_schema_version, read_document
from satedge_simulator.io.contact_plan.table import ContactPlan


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
    kind: str
    links: list[PeriodicLinkDoc] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value)


def read_periodic(path: Path, horizon_s: float | None) -> ContactPlan:
    """The contact plan in ``path``, with the windows that open before ``horizon_s``.

    Raises:
        ScenarioError: If the horizon is missing, or the windows of a link would overlap.
    """
    if horizon_s is None:
        raise ScenarioError(
            "un contact plan periodico richiede l'orizzonte della simulazione"
        )
    document = read_document(path, PeriodicContactPlanDoc)
    windows: dict[tuple[str, str], WindowSet] = {}
    for link in document.links:
        try:
            windows[(link.a, link.b)] = WindowSet.periodic(
                link.first_start_s, link.period_s, link.duration_s, horizon_s
            )
        except ScenarioError as error:
            raise ScenarioError(f"link {link.a}-{link.b}: {error}") from error
    return ContactPlan(windows)
