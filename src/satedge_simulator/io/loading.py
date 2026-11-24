"""Reading of the input files: from the text of a file to the objects of the simulator."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.errors import DocumentError, ScenarioError
from satedge_simulator.io.contact_plan import ContactPlan
from satedge_simulator.io.documents import ContactPlanDoc


def load_contact_plan(path: str | Path) -> ContactPlan:
    """Read the contact plan in ``path``.

    Raises:
        DocumentError: If the file cannot be read, is not valid YAML, or does not match the
            schema. The message names the file.
    """
    document = _read_document(path, ContactPlanDoc)
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


def _read_document[T: ContactPlanDoc](path: str | Path, schema: type[T]) -> T:
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except OSError as error:
        raise DocumentError(
            f"{path}: cannot read the file ({error.strerror})"
        ) from error
    except yaml.YAMLError as error:
        raise DocumentError(f"{path}: invalid YAML: {error}") from error
    try:
        return schema.model_validate(data)
    except ValidationError as error:
        raise DocumentError(f"{path}: {error}") from error
