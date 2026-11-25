"""The source of the stochastic workload: a process that submits each request at its arrival."""

from __future__ import annotations

from collections.abc import Generator

import simpy

from satedge_simulator.generation.generator import RequestGenerator
from satedge_simulator.runtime.ground import GroundRuntime


def workload_source(
    env: simpy.Environment,
    generator: RequestGenerator,
    ground: GroundRuntime,
    end_s: float,
) -> Generator[simpy.Event, object]:
    """Submit the requests of ``generator`` to ``ground`` at their arrivals, until ``end_s``.

    The requests are drawn at run time, at their arrival: the ground segment never sees a
    request before it arrives, as in the real system.
    """
    while True:
        yield env.timeout(generator.next_interarrival_s())
        if env.now >= end_s:
            return
        ground.submit(generator.request(env.now))
