"""Conventions of the input files: the values a file may leave out.

They belong to the reading of the files, not to the domain: the domain always receives the
values, explicit or filled in here.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from satedge_simulator.domain.requests import Priority

DEFAULT_DEADLINE_AFTER_RELEASE_S: Mapping[Priority, float] = MappingProxyType(
    {Priority.URGENT: 7200.0, Priority.NON_URGENT: 25200.0}
)
"""Delay after the release within which each class must be delivered when the file does not
state the deadline: 2 hours for the urgent requests, 7 hours for the others."""
