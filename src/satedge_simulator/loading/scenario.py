"""Scenario loading: the scenario files, turned into the simulation of the domain.

The files are read by :mod:`satedge_simulator.io.scenario`. This module builds the objects of the
domain from them.
"""

from __future__ import annotations

from pathlib import Path

from satedge_simulator.io.scenario import ScenarioFiles, read_scenario


def load_scenario(path: str | Path) -> ScenarioFiles:
    """Read the scenario in ``path`` and build its simulation.

    Raises:
        DocumentError: If a file is not valid, or the files do not agree with each other.
        NotImplementedError: Always, for now: the simulation settings are not yet in any file,
            so the domain scenario cannot be built.
    """
    read_scenario(path)
    raise NotImplementedError(
        "load_scenario: the simulation settings are not in any file yet"
    )
