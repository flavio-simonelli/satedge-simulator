"""The random quantities of a request, each with its stream of the generator."""

from __future__ import annotations

from enum import IntEnum


class Quantity(IntEnum):
    """A random quantity of the workload; its value is the index of its stream.

    One stream per quantity: changing the distribution of one does not change the numbers of
    the others, and two runs with the same seed and different planners see the same workload
    (common random numbers).
    """

    ARRIVALS = 0
    PRIORITY = 1
    ACQUISITION = 2
    ORIGIN = 3
    RAW = 4
    STAGES = 5
    WORK = 6
    RATIO = 7
    FINAL = 8
