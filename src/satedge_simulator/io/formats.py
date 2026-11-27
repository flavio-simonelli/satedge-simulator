"""The formats the documents are read and written in.

A format is a :class:`Codec`: how its text is parsed, how a document is written, and which file
suffixes name it. To add a format, add a codec here and list it in :data:`CODECS`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from satedge_simulator.errors import DocumentError


@dataclass(frozen=True, slots=True)
class Codec:
    """One format: its name, the suffixes of its files, and how it is parsed and written.

    Attributes:
        name: The name of the format, as the messages spell it.
        suffixes: The file suffixes that name this format, in lower case.
        parse: Turns the text of a file into plain data. Raises ``error`` if the text is not valid.
        error: The exception that ``parse`` raises for invalid text.
        dump: Turns a document into the text of a file.
    """

    name: str
    suffixes: tuple[str, ...]
    parse: Callable[[str], Any]
    error: type[Exception]
    dump: Callable[[BaseModel], str]


def _dump_yaml(document: BaseModel) -> str:
    data = document.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _dump_json(document: BaseModel) -> str:
    return document.model_dump_json(indent=2) + "\n"


YAML = Codec(
    name="YAML",
    suffixes=(".yaml", ".yml"),
    parse=yaml.safe_load,
    error=yaml.YAMLError,
    dump=_dump_yaml,
)

JSON = Codec(
    name="JSON",
    suffixes=(".json",),
    parse=json.loads,
    error=json.JSONDecodeError,
    dump=_dump_json,
)

CODECS: tuple[Codec, ...] = (YAML, JSON)


def codec_for(path: str | Path) -> Codec:
    """The codec of the file ``path``, chosen by its suffix.

    Raises:
        DocumentError: If no codec has the suffix of ``path``.
    """
    suffix = Path(path).suffix.lower()
    for codec in CODECS:
        if suffix in codec.suffixes:
            return codec
    known = ", ".join(s for codec in CODECS for s in codec.suffixes)
    raise DocumentError(
        f"{path}: the format of the file is unknown, its suffix must be one of: {known}"
    )
