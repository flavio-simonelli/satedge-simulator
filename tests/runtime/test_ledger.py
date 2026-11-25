"""Tests of the ledger of the data."""

import pytest
import simpy

from satedge_simulator.errors import StateError
from satedge_simulator.runtime.ledger import DataKey, DataLedger


def test_a_data_item_is_complete_once() -> None:
    env = simpy.Environment()
    ledger = DataLedger(env)
    key = DataKey("R1", 0, "A")
    assert not ledger.is_complete(key)
    ledger.mark_complete(key)
    assert ledger.is_complete(key)
    with pytest.raises(StateError, match="twice"):
        ledger.mark_complete(key)


def test_the_same_event_is_returned_for_the_same_key() -> None:
    env = simpy.Environment()
    ledger = DataLedger(env)
    key = DataKey("R1", 0, "A")
    assert ledger.complete_event(key) is ledger.complete_event(key)
