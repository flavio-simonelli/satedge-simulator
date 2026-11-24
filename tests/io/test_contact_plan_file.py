"""Tests of the reading of the contact plan file."""

from pathlib import Path

import pytest

from satedge_simulator.domain.intervals import Window
from satedge_simulator.errors import DocumentError
from satedge_simulator.io.contact_plan import load_contact_plan

VALID = """\
schema_version: "1.0.0"
links:
  - {a: COM1, b: GS, windows: [{start_s: 100, end_s: 280}, {start_s: 2820, end_s: 3000}]}
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "contact_plan.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_the_windows_of_each_link(tmp_path: Path) -> None:
    plan = load_contact_plan(write(tmp_path, VALID))
    windows = plan.windows_of("GS", "COM1")
    assert list(windows) == [Window(100.0, 280.0), Window(2820.0, 3000.0)]


def test_unknown_field_is_rejected_with_the_file_name(tmp_path: Path) -> None:
    path = write(tmp_path, VALID + "unexpected: true\n")
    with pytest.raises(DocumentError, match="contact_plan.yaml"):
        load_contact_plan(path)


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    path = write(tmp_path, VALID.replace('"1.0.0"', '"2.0.0"'))
    with pytest.raises(DocumentError, match="schema version"):
        load_contact_plan(path)


def test_overlapping_windows_are_rejected(tmp_path: Path) -> None:
    text = VALID.replace("{start_s: 2820, end_s: 3000}", "{start_s: 200, end_s: 300}")
    with pytest.raises(DocumentError):
        load_contact_plan(write(tmp_path, text))


def test_missing_file_is_a_document_error(tmp_path: Path) -> None:
    with pytest.raises(DocumentError):
        load_contact_plan(tmp_path / "absent.yaml")


def test_invalid_yaml_is_a_document_error(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="invalid YAML"):
        load_contact_plan(write(tmp_path, "links: [unclosed"))
