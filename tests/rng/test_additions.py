"""Tests of what this project adds to the ported libraries of Park and Geyer.

The ports stay faithful to the original and are trusted; these tests cover only what the
original does not have: generators without global state, the explicit seed, the stream that
runs out, the source passed to each variate, the balanced hyperexponential, the checks on the
parameters.
"""

import statistics
from collections.abc import Iterator

import pytest

from satedge_simulator.errors import InputError, StreamExhaustedError
from satedge_simulator.rng.rngs import MODULUS, STREAM_LENGTH, STREAMS, MultiStreamRng
from satedge_simulator.rng.rvgs import (
    balanced_hyperexponential,
    exponential,
    hyperexponential,
    uniform,
)
from satedge_simulator.rng.rvms import idf_student


class Scripted:
    """A source that returns the given uniforms, in order."""

    def __init__(self, *values: float) -> None:
        self._values: Iterator[float] = iter(values)

    def random(self) -> float:
        return next(self._values)


# rngs: each generator owns its states, the seed is explicit, a stream does not repeat.


def test_drawing_from_one_stream_leaves_the_others_as_they_are() -> None:
    rng = MultiStreamRng(42)
    before = rng.stream(1).state
    for _ in range(100):
        rng.stream(0).random()
    assert rng.stream(1).state == before
    assert rng.stream(0).drawn == 100


def test_two_generators_do_not_share_their_states() -> None:
    a, b = MultiStreamRng(42), MultiStreamRng(42)
    a.stream(0).random()
    assert b.stream(0).drawn == 0


def test_a_stream_is_one_object_per_index() -> None:
    rng = MultiStreamRng(42)
    assert rng.stream(3) is rng.stream(3)


def test_the_same_seed_gives_the_same_numbers() -> None:
    a, b = MultiStreamRng(42).stream(5), MultiStreamRng(42).stream(5)
    assert [a.random() for _ in range(100)] == [b.random() for _ in range(100)]


def test_a_stream_that_used_up_its_arc_raises_instead_of_repeating() -> None:
    stream = MultiStreamRng(42).stream(0)
    stream._drawn = STREAM_LENGTH - 1  # skip ahead: the arc has one number left
    stream.random()
    assert stream.remaining == 0
    with pytest.raises(StreamExhaustedError, match="stream 0"):
        stream.random()


@pytest.mark.parametrize("seed", [0, -1, MODULUS])
def test_the_seed_must_be_a_state_of_the_generator(seed: int) -> None:
    with pytest.raises(InputError, match="seed"):
        MultiStreamRng(seed)


@pytest.mark.parametrize("index", [-1, STREAMS])
def test_the_stream_index_must_exist(index: int) -> None:
    rng = MultiStreamRng(42)
    with pytest.raises(InputError, match="stream"):
        rng.stream(index)


# rvgs: the source is passed to each variate; the balanced hyperexponential is new.


def test_the_hyperexponential_draws_branch_and_value_from_the_same_source() -> None:
    # 0.95 >= 1 - p picks the first branch, then the exponential uses 0.5
    value = hyperexponential(Scripted(0.95, 0.5), 0.1, 10.0, 1.0)
    assert value == pytest.approx(10.0 * 0.6931471805599453)


def test_balanced_means_split_the_mean_in_two_halves() -> None:
    p, m1, m2 = balanced_hyperexponential(mean=4.0, cv=4.0)
    assert p * m1 == pytest.approx(2.0)
    assert (1 - p) * m2 == pytest.approx(2.0)
    # the second moment of a hyperexponential gives back the coefficient of variation
    second = 2 * (p * m1**2 + (1 - p) * m2**2)
    assert (second - 4.0**2) ** 0.5 / 4.0 == pytest.approx(4.0)


def test_the_hyperexponential_mean_on_many_draws() -> None:
    stream = MultiStreamRng(123_456_789).stream(9)
    p, m1, m2 = balanced_hyperexponential(mean=4.0, cv=2.0)
    sample = [hyperexponential(stream, p, m1, m2) for _ in range(100_000)]
    assert statistics.fmean(sample) == pytest.approx(4.0, rel=0.03)


# The checks on the parameters: the original libraries have none.


def test_invalid_variate_parameters_are_scenario_errors() -> None:
    stream = Scripted(0.5)
    with pytest.raises(InputError, match="Exponential"):
        exponential(stream, 0.0)
    with pytest.raises(InputError, match="Uniform"):
        uniform(stream, 3.0, 3.0)
    with pytest.raises(InputError, match="coefficiente di variazione"):
        balanced_hyperexponential(1.0, 1.0)


def test_the_quantile_needs_a_probability_and_degrees_of_freedom() -> None:
    with pytest.raises(InputError):
        idf_student(10, 1.0)
    with pytest.raises(InputError):
        idf_student(0, 0.5)
