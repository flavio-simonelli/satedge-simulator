"""Shared plumbing of the input files: the base of the schemas and the reading of one document."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from satedge_simulator.errors import DocumentError

SUPPORTED_MAJOR_VERSION = "1."


class Document(BaseModel):
    """Base of every schema: unknown fields are errors, not silently ignored."""

    model_config = ConfigDict(extra="forbid")


def check_schema_version(value: str) -> str:
    """Accept only the supported major version of the schema."""
    if not value.startswith(SUPPORTED_MAJOR_VERSION):
        raise ValueError(f"unsupported schema version {value!r}, expected 1.x")
    return value


def read_document[T: BaseModel](path: str | Path, schema: type[T]) -> T:
    """Read the YAML file ``path`` and validate it against ``schema``.

    Raises:
        DocumentError: If the file cannot be read, is not valid YAML, or does not match the
            schema. The message names the file.
    """
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
