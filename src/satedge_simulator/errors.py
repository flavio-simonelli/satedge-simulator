"""Exceptions of the simulator.

Violations of the plan during the execution are not exceptions: they are a result of the
simulation (see :mod:`satedge_simulator.domain.violations`). The exceptions below signal invalid
inputs, a planner that fails, or a defect of the simulator itself.
"""


class SimulatorError(Exception):
    """Base of every exception raised by the simulator."""


class ScenarioError(SimulatorError):
    """The scenario is inconsistent: invalid parameters, duplicate or unknown identifiers."""


class DocumentError(ScenarioError):
    """A scenario file cannot be read or is not valid."""


class PlannerError(SimulatorError):
    """The planner could not produce a decision, or produced an unusable one."""


class PlanExecutionError(SimulatorError):
    """A violation of the plan in strict mode: the simulation stops at the first one."""


class StateError(SimulatorError):
    """Internal inconsistency of the simulator: a defect, not a violation of the plan."""


class RandomParameterError(SimulatorError, ValueError):
    """A parameter out of range for the random number libraries: a seed, a stream index, the
    parameter of a distribution, a probability.

    It is a :class:`ValueError` too, since the libraries know nothing of the scenario: whoever
    takes the parameter from the scenario validates it first and raises :class:`ScenarioError`.
    """


class StreamExhaustedError(SimulatorError):
    """A stream of random numbers used up its share of the cycle of the generator.

    Going on would repeat the numbers of the next stream, so the replications would no longer
    be independent.
    """
