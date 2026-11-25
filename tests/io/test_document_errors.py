"""Tests of the messages of the errors in the input files, which the user reads in Italian."""

from pathlib import Path

import pytest
from pydantic import Field

from satedge_simulator.errors import DocumentError
from satedge_simulator.io.base import Document, read_document


class Sample(Document):
    name: str
    size: float = Field(gt=0)


def test_validation_errors_are_described_field_by_field(tmp_path: Path) -> None:
    path = tmp_path / "sample.yaml"
    path.write_text("size: -1\nextra: 3\n", encoding="utf-8")
    with pytest.raises(DocumentError) as raised:
        read_document(path, Sample)
    assert str(raised.value).splitlines() == [
        f"{path}: il documento non è valido:",
        "  name: campo obbligatorio mancante",
        "  size: deve essere maggiore di 0.0",
        "  extra: campo non previsto",
    ]


def test_a_missing_file_says_so(tmp_path: Path) -> None:
    path = tmp_path / "absent.yaml"
    with pytest.raises(DocumentError) as raised:
        read_document(path, Sample)
    assert (
        str(raised.value) == f"{path}: impossibile leggere il file (il file non esiste)"
    )
