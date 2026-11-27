"""Shared plumbing of the files: the base of the schemas, and the reading and writing of one document.

The format of a file is chosen by its suffix, see :mod:`satedge_simulator.io.formats`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from satedge_simulator.errors import DocumentError
from satedge_simulator.io.formats import Codec, codec_for

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")


class Document(BaseModel):
    """Base of every schema: unknown fields are errors, not silently ignored."""

    model_config = ConfigDict(extra="forbid")


class VersionedDocument(Document):
    """Base of the files that carry a ``schema_version``.

    Each subclass declares the highest version it reads, as ``SUPPORTED_VERSION``. The kinds of
    file evolve separately, so each one has its own.
    """

    schema_version: str
    SUPPORTED_VERSION: ClassVar[tuple[int, int]]

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, value: str) -> str:
        return check_schema_version(value, cls.SUPPORTED_VERSION)


def check_schema_version(value: str, supported: tuple[int, int]) -> str:
    """Accept a schema version of the form ``MAJOR.MINOR`` or ``MAJOR.MINOR.PATCH``.

    ``supported`` is the highest ``(major, minor)`` the schema of this file reads. The version
    must have the same major, and a minor no newer than ``supported``. The patch number does
    not matter. Each kind of file has its own ``supported``, so the kinds evolve separately.

    Raises:
        ValueError: If the version is malformed, has another major, or a newer minor.
    """
    match = _VERSION_PATTERN.match(value)
    if match is None:
        raise ValueError(
            f"schema_version {value!r} is not a version: expected MAJOR.MINOR or MAJOR.MINOR.PATCH"
        )
    major, minor = int(match.group(1)), int(match.group(2))
    supported_major, supported_minor = supported
    if major != supported_major:
        raise ValueError(
            f"schema_version {value!r} has major {major}, but this file reads only "
            f"major {supported_major}"
        )
    if minor > supported_minor:
        raise ValueError(
            f"schema_version {value!r} is newer than this simulator supports for this file "
            f"({supported_major}.{supported_minor})"
        )
    return value


def _load(path: str | Path, codec: Codec | None) -> Any:
    """The plain data of the file ``path``, parsed in its format."""
    codec = codec or codec_for(path)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise DocumentError(
            f"{path}: cannot read the file ({error.strerror or error})"
        ) from error
    try:
        return codec.parse(text)
    except codec.error as error:
        raise DocumentError(f"{path}: invalid {codec.name}: {error}") from error


def _validate[T: BaseModel](path: str | Path, schema: type[T], data: Any) -> T:
    """``data`` validated against ``schema``; the errors name the file."""
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


def read_document[T: BaseModel](
    path: str | Path, schema: type[T], codec: Codec | None = None
) -> T:
    """Read the file ``path`` and validate it against ``schema``.

    The format is ``codec``, or else the one named by the suffix of ``path``.

    Raises:
        DocumentError: If the format is unknown, the file cannot be read, its text is not valid
            in its format, or it does not match the schema. The message names the file.
    """
    return _validate(path, schema, _load(path, codec))


class Registry[T: Document]:
    """The variants of one kind of file, by their value.

    A file names its variant with ``field`` (for example ``method``). Each variant class registers
    itself with :meth:`variant`, so the registry never lists the variants: a new variant is a new
    class, and the others are not touched. Each class states which version of its file it reads.
    """

    def __init__(self, field: str) -> None:
        self._field = field
        self._schemas: dict[str, type[T]] = {}

    def variant(self, value: str) -> Callable[[type[T]], type[T]]:
        """Decorator: register the class under ``value``."""

        def register(schema: type[T]) -> type[T]:
            if value in self._schemas:
                raise ValueError(f"{self._field} {value!r} is already registered")
            self._schemas[value] = schema
            return schema

        return register

    def choose(self, path: str | Path, data: Any) -> type[T]:
        """The schema that reads ``data``, from its variant.

        Raises:
            DocumentError: If the data is not a mapping, or names no known variant. The message
                names the file.
        """
        if not isinstance(data, dict):
            raise DocumentError(f"{path}: the document is not a mapping of fields")
        value = data.get(self._field)
        schema = self._schemas.get(value) if isinstance(value, str) else None
        if schema is None:
            known = ", ".join(sorted(self._schemas))
            raise DocumentError(
                f"{path}: {self._field} {value!r} is not supported; supported: {known}"
            )
        return schema


def read_variant[T: Document](
    path: str | Path, registry: Registry[T], codec: Codec | None = None
) -> T:
    """Read the file ``path``, and validate it against the schema its variant selects.

    Raises:
        DocumentError: If the file cannot be read or is not valid, or names no known variant.
            The message names the file.
    """
    data = _load(path, codec)
    return _validate(path, registry.choose(path, data), data)


def write_document(
    path: str | Path, document: BaseModel, codec: Codec | None = None
) -> None:
    """Write ``document`` to the file ``path``, creating its directory if needed.

    The format is ``codec``, or else the one named by the suffix of ``path``.

    Raises:
        DocumentError: If the format is unknown or the file cannot be written. The message names
            the file.
    """
    codec = codec or codec_for(path)
    file = Path(path)
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(codec.dump(document), encoding="utf-8")
    except OSError as error:
        raise DocumentError(
            f"{path}: cannot write the file ({error.strerror or error})"
        ) from error
