"""Multi-stream Lehmer random number generator (rngs).

The generator is ``x' = a·x mod m`` with ``m = 2³¹ − 1`` and ``a = 48271``: a full-period
generator, whose ``m − 1`` states form one cycle. The cycle is cut into 256 streams, each one an
arc of ``STREAM_LENGTH`` consecutive states that starts where the jump multiplier puts it, so
the streams never share a number.

Differences from the original libraries, which kept one global current stream:

- each :class:`MultiStreamRng` owns its states, and each consumer holds its own :class:`Stream`,
  so drawing from one stream never changes which stream another consumer draws from;
- the seed is always explicit: no seed from the clock or from the keyboard, every run is
  reproducible;
- a stream that would run into the next one raises :class:`StreamExhaustedError`, instead of
  silently repeating its numbers.

Algorithm, constants and check values: Steve Park and Dave Geyer, rngs.c (09-22-98); Python
translation by Philip Steele (2014, MIT License).
"""

from __future__ import annotations

from satedge_simulator.errors import ScenarioError, StreamExhaustedError

MODULUS = 2_147_483_647
"""``m = 2³¹ − 1``, a prime: the generator has period ``m − 1``."""

MULTIPLIER = 48_271
"""``a``, a full-period multiplier that is modulus compatible."""

CHECK = 399_268_537
"""State after 10 000 draws from the state 1: the test of a correct implementation."""

STREAMS = 256
"""Number of streams."""

JUMP_MULTIPLIER = 22_925
"""``a^STREAM_LENGTH mod m``: the state of a stream is the previous one times this value."""

STREAM_LENGTH = 8_367_782
"""Draws between the initial states of two consecutive streams."""

DEFAULT_SEED = 123_456_789
"""The default seed of the original libraries."""


def _lehmer_step(x: int, a: int) -> int:
    """``a·x mod m`` by Schrage's method, as the original, so no product exceeds ``m``."""
    q, r = divmod(MODULUS, a)
    t = a * (x % q) - r * (x // q)
    return t if t > 0 else t + MODULUS


class Stream:
    """One stream of the generator: the uniform random numbers of one source of randomness."""

    __slots__ = ("_drawn", "_index", "_state")

    def __init__(self, index: int, state: int) -> None:
        self._index = index
        self._state = state
        self._drawn = 0

    @property
    def index(self) -> int:
        return self._index

    @property
    def state(self) -> int:
        """The current state, the last number drawn times ``m``."""
        return self._state

    @property
    def drawn(self) -> int:
        """Numbers drawn since the seeds were planted."""
        return self._drawn

    @property
    def remaining(self) -> int:
        """Numbers that can still be drawn before reaching the next stream."""
        return STREAM_LENGTH - self._drawn

    def random(self) -> float:
        """A uniform random number in ``(0, 1)``: between ``1/m`` and ``1 − 1/m``.

        Raises:
            StreamExhaustedError: If the stream used up its arc of the cycle.
        """
        if self._drawn >= STREAM_LENGTH:
            raise StreamExhaustedError(
                f"lo stream {self._index} ha esaurito i suoi {STREAM_LENGTH} numeri: "
                "proseguire ripeterebbe i numeri dello stream successivo"
            )
        self._state = _lehmer_step(self._state, MULTIPLIER)
        self._drawn += 1
        return self._state / MODULUS


class MultiStreamRng:
    """The 256 streams of the generator, planted from one explicit seed.

    The seed is the initial state of stream 0; the initial state of stream ``j`` is the one of
    stream ``j − 1`` times the jump multiplier. Replications that keep drawing from the same
    instance go on along the same arcs, so no number is used twice across them.

    Args:
        seed: The initial state of stream 0, with ``0 < seed < m``.

    Raises:
        ScenarioError: If the seed is out of range.
    """

    def __init__(self, seed: int = DEFAULT_SEED) -> None:
        if not 0 < seed < MODULUS:
            raise ScenarioError(
                f"il seed deve essere compreso tra 1 e {MODULUS - 1}, invece è {seed}"
            )
        self._seed = seed
        states = [seed]
        for _ in range(1, STREAMS):
            states.append(_lehmer_step(states[-1], JUMP_MULTIPLIER))
        self._streams = tuple(Stream(j, x) for j, x in enumerate(states))

    @property
    def seed(self) -> int:
        """The seed the streams were planted from."""
        return self._seed

    def stream(self, index: int) -> Stream:
        """Stream ``index``: always the same object for the same index.

        Raises:
            ScenarioError: If the index is not between 0 and 255.
        """
        if not 0 <= index < STREAMS:
            raise ScenarioError(
                f"lo stream deve essere compreso tra 0 e {STREAMS - 1}, invece è {index}"
            )
        return self._streams[index]

    @property
    def states(self) -> tuple[int, ...]:
        """The current state of every stream, as the original ``getSeed`` per stream."""
        return tuple(s.state for s in self._streams)
