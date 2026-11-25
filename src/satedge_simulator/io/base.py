"""Shared plumbing of the input files: the base of the schemas and the reading of one document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
        raise ValueError(f"versione dello schema non supportata {value!r}, attesa 1.x")
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
            f"{path}: impossibile leggere il file ({_reason(error)})"
        ) from error
    except yaml.YAMLError as error:
        raise DocumentError(f"{path}: YAML non valido: {error}") from error
    try:
        return schema.model_validate(data)
    except ValidationError as error:
        raise DocumentError(f"{path}: {describe(error)}") from error


def describe(error: ValidationError) -> str:
    """The errors of a validation, one per line, in Italian.

    The frequent kinds are translated; the others keep the message of pydantic.
    """
    lines = [
        f"{'.'.join(str(part) for part in e['loc']) or 'documento'}: {_message(e)}"
        for e in error.errors()
    ]
    return "\n  ".join(["il documento non è valido:", *lines])


_MESSAGES = {
    "missing": "campo obbligatorio mancante",
    "extra_forbidden": "campo non previsto",
    "float_type": "deve essere un numero",
    "float_parsing": "deve essere un numero",
    "int_type": "deve essere un numero intero",
    "int_parsing": "deve essere un numero intero",
    "string_type": "deve essere un testo",
    "bool_type": "deve essere vero o falso",
    "bool_parsing": "deve essere vero o falso",
    "list_type": "deve essere una lista",
    "dict_type": "deve essere una mappa di campi",
    "model_type": "deve essere una mappa di campi",
    "finite_number": "deve essere un numero finito",
    "greater_than": "deve essere maggiore di {gt}",
    "greater_than_equal": "deve essere maggiore o uguale a {ge}",
    "less_than": "deve essere minore di {lt}",
    "less_than_equal": "deve essere minore o uguale a {le}",
    "too_short": "deve avere almeno {min_length} elementi",
    "too_long": "deve avere al più {max_length} elementi",
    "literal_error": "deve essere uno tra {expected}",
    "enum": "deve essere uno tra {expected}",
}


def _message(error: Any) -> str:
    if error["type"] == "value_error":
        return str(error["ctx"]["error"])  # our validators: already in Italian
    template = _MESSAGES.get(error["type"])
    if template is None:
        return str(error["msg"])
    return template.format(**error.get("ctx", {}))


def _reason(error: OSError) -> str:
    if isinstance(error, FileNotFoundError):
        return "il file non esiste"
    if isinstance(error, IsADirectoryError):
        return "è una cartella"
    if isinstance(error, PermissionError):
        return "permesso negato"
    return error.strerror or str(error)
