"""Tests of the check of the schema version of the input files."""

import pytest

from satedge_simulator.io.base import check_schema_version

SUPPORTED = (1, 0)


@pytest.mark.parametrize("value", ["1.0", "1.0.0", "1.0.7", "1.0.12"])
def test_supported_versions_are_accepted(value: str) -> None:
    assert check_schema_version(value, SUPPORTED) == value


def test_the_supported_minor_is_accepted() -> None:
    major, minor = SUPPORTED
    assert check_schema_version(f"{major}.{minor}.0", SUPPORTED) == f"{major}.{minor}.0"


@pytest.mark.parametrize("value", ["1.1", "1.1.0", "1.9.3"])
def test_a_newer_minor_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="newer than this simulator supports"):
        check_schema_version(value, SUPPORTED)


@pytest.mark.parametrize("value", ["2.0", "2.0.0", "0.9.0", "10.0.0"])
def test_another_major_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="reads only major 1"):
        check_schema_version(value, SUPPORTED)


@pytest.mark.parametrize(
    "value", ["1", "1.", "1.x", "1.0.0.0", "v1.0", "", "1.0-beta", " 1.0"]
)
def test_a_malformed_version_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="is not a version"):
        check_schema_version(value, SUPPORTED)
