"""Tests of the event log."""

import io
import json

from satedge_simulator.domain.violations import ViolationKind
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.event_log import JsonlEventLog
from satedge_simulator.observe.notifications import RequestArrived, ViolationRaised


def test_each_notification_is_one_json_line_with_its_type() -> None:
    stream = io.StringIO()
    bus = EventBus()
    JsonlEventLog(stream).attach(bus)
    bus.publish(RequestArrived(1.0, "R1"))
    bus.publish(ViolationRaised(2.5, "R1", ViolationKind.PLMM_FULL, "A"))
    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert lines == [
        {"type": "RequestArrived", "time": 1.0, "request_id": "R1"},
        {
            "type": "ViolationRaised",
            "time": 2.5,
            "request_id": "R1",
            "kind": "plmm_full",
            "node": "A",
        },
    ]
