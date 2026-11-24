"""Schemas of the input files: what each file must contain, checked when it is read."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Document(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WindowDoc(_Document):
    """A window of time, in seconds."""

    start_s: float
    end_s: float


class LinkWindowsDoc(_Document):
    """The visibility windows between two nodes."""

    a: str
    b: str
    windows: list[WindowDoc] = Field(default_factory=list)


class ContactPlanDoc(_Document):
    """A contact plan file: the visibility windows of the links that are not always available."""

    schema_version: str
    links: list[LinkWindowsDoc] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_major(cls, value: str) -> str:
        if not value.startswith("1."):
            raise ValueError(f"unsupported schema version {value!r}, expected 1.x")
        return value
