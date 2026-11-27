"""Exceptions of the simulator.

Violations of the plan during the execution are not exceptions: they are a result of the
simulation (see :mod:`satedge_simulator.domain.violations`). The exceptions below signal invalid
inputs, a planner that fails, or a defect of the simulator itself.
"""


class SimulatorError(Exception):
    """Base of every exception raised by the simulator."""


class DomainError(SimulatorError):
    """An object of the domain breaks one of its invariants: a value out of range, an unknown
    or duplicate identifier, an inconsistent combination of objects."""


class InputError(SimulatorError):
    """A value given from outside is not valid: an argument of a call, or a setting."""


class DocumentError(InputError):
    """A file cannot be read or is not valid. The message names the file."""


class PlannerError(SimulatorError):
    """The planner could not produce a decision, or produced an unusable one."""


class PlanExecutionError(SimulatorError):
    """A violation of the plan in strict mode: the simulation stops at the first one."""


class StateError(SimulatorError):
    """Internal inconsistency of the simulator: a defect, not a violation of the plan."""


class StreamExhaustedError(SimulatorError):
    """A stream of random numbers used up its share of the cycle of the generator.

    Going on would repeat the numbers of the next stream, so the replications would no longer
    be independent.
    """
