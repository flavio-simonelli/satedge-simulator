"""Tests of the multi-stream Lehmer generator, with the check values of the original library."""

import pytest

from satedge_simulator.errors import ScenarioError, StreamExhaustedError
from satedge_simulator.rng.rngs import (
    CHECK,
    JUMP_MULTIPLIER,
    MODULUS,
    MULTIPLIER,
    STREAM_LENGTH,
    STREAMS,
    MultiStreamRng,
)


def test_ten_thousand_draws_from_the_state_one_reach_the_check_value() -> None:
    stream = MultiStreamRng(1).stream(0)
    for _ in range(10_000):
        stream.random()
    assert stream.state == CHECK


def test_planting_from_one_puts_the_jump_multiplier_in_stream_one() -> None:
    assert MultiStreamRng(1).stream(1).state == JUMP_MULTIPLIER


def test_the_jump_multiplier_skips_one_stream_length_of_the_cycle() -> None:
    assert pow(MULTIPLIER, STREAM_LENGTH, MODULUS) == JUMP_MULTIPLIER


def test_each_stream_starts_one_jump_after_the_previous() -> None:
    states = MultiStreamRng(123_456_789).states
    assert len(states) == STREAMS
    assert states[0] == 123_456_789
    assert all(
        states[j] == states[j - 1] * JUMP_MULTIPLIER % MODULUS
        for j in range(1, STREAMS)
    )


def test_the_numbers_lie_strictly_between_zero_and_one() -> None:
    stream = MultiStreamRng(MODULUS - 1).stream(7)
    values = [stream.random() for _ in range(1000)]
    assert all(1 / MODULUS <= u <= 1 - 1 / MODULUS for u in values)


def test_the_same_seed_gives_the_same_numbers() -> None:
    a, b = MultiStreamRng(42).stream(5), MultiStreamRng(42).stream(5)
    assert [a.random() for _ in range(100)] == [b.random() for _ in range(100)]


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


def test_a_stream_that_used_up_its_arc_raises_instead_of_repeating() -> None:
    stream = MultiStreamRng(42).stream(0)
    stream._drawn = STREAM_LENGTH - 1  # skip ahead: the arc has one number left
    stream.random()
    assert stream.remaining == 0
    with pytest.raises(StreamExhaustedError, match="stream 0"):
        stream.random()


@pytest.mark.parametrize("seed", [0, -1, MODULUS])
def test_the_seed_must_be_a_state_of_the_generator(seed: int) -> None:
    with pytest.raises(ScenarioError, match="seed"):
        MultiStreamRng(seed)


@pytest.mark.parametrize("index", [-1, STREAMS])
def test_the_stream_index_must_exist(index: int) -> None:
    with pytest.raises(ScenarioError, match="stream"):
        MultiStreamRng(42).stream(index)
