"""Shared plumbing of the input files: the base of the schemas and the reading of one document."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from satedge_simulator.errors import DocumentError

SUPPORTED_VERSION = (1, 0)
"""The highest schema version this simulator reads, as (major, minor).

Minor versions only add optional fields, so any minor up to this one is read; a new major
version is not read at all.
"""

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")


class Document(BaseModel):
    """Base of every schema: unknown fields are errors, not silently ignored."""

    model_config = ConfigDict(extra="forbid")


def check_schema_version(value: str) -> str:
    """Accept a schema version of the form ``MAJOR.MINOR`` or ``MAJOR.MINOR.PATCH``.

    The version must be supported: the same major as ``SUPPORTED_VERSION`` and a minor no newer
    than it. The patch number does not matter.

    Raises:
        ValueError: If the version is malformed, has another major, or a newer minor.
    """
    match = _VERSION_PATTERN.match(value)
    if match is None:
        raise ValueError(
            f"schema_version {value!r} is not a version: expected MAJOR.MINOR or MAJOR.MINOR.PATCH"
        )
    major, minor = int(match.group(1)), int(match.group(2))
    supported_major, supported_minor = SUPPORTED_VERSION
    if major != supported_major:
        raise ValueError(
            f"schema_version {value!r} has major {major}, but this simulator reads only "
            f"major {supported_major}"
        )
    if minor > supported_minor:
        raise ValueError(
            f"schema_version {value!r} is newer than this simulator supports "
            f"({supported_major}.{supported_minor})"
        )
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
            f"{path}: cannot read the file ({error.strerror or error})"
        ) from error
    except yaml.YAMLError as error:
        raise DocumentError(f"{path}: invalid YAML: {error}") from error
    try:
        return schema.model_validate(data)
    except ValidationError as error:
        lines = [
            f"{'.'.join(str(part) for part in e['loc']) or 'document'}: {e['msg']}"
            for e in error.errors()
        ]
        raise DocumentError(
            "\n  ".join([f"{path}: the document is not valid:", *lines])
        ) from error
