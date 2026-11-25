"""Tests of what the runtime publishes, on the scenario of ``one_satellite``."""

import pytest
import simpy
from one_satellite import (
    EPS,
    LEAD_TIME_S,
    ScriptedPlanner,
    actions,
    constellation,
    request,
)

from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import (
    EpochPlanned,
    Notification,
    PlmmChanged,
    RequestRejected,
    TaskEnded,
    TransferEnded,
)
from satedge_simulator.planning.epochs import planning_epochs
from satedge_simulator.planning.rolling_planner import RollingPlanner
from satedge_simulator.runtime.ground import GroundRuntime
from satedge_simulator.runtime.installer import PlanInstaller
from satedge_simulator.runtime.ledger import DataLedger
from satedge_simulator.runtime.network import NetworkRuntime


def run(planner: ScriptedPlanner) -> list[Notification]:
    env = simpy.Environment()
    bus = EventBus()
    heard: list[Notification] = []
    bus.subscribe(Notification, heard.append)
    net = constellation()
    network = NetworkRuntime(env, net, EPS, bus)
    ledger = DataLedger(env)
    GroundRuntime(
        env,
        (request(),),
        planning_epochs(net, lead_time_s=LEAD_TIME_S, end_s=2000.0),
        RollingPlanner(planner, net),
        network,
        ledger,
        PlanInstaller(env, network, ledger, EPS, bus),
        EPS,
        bus=bus,
    )
    env.run()
    return heard


def test_the_life_of_a_delivered_request_in_notifications() -> None:
    heard = run(ScriptedPlanner({"R1": actions(120.0, 150.0)}))
    assert [(type(n).__name__, n.time) for n in heard] == [
        ("RequestArrived", 10.0),
        ("PlmmChanged", 20.0),  # the raw data are acquired
        ("RequestAccepted", 50.0),
        ("EpochPlanned", 50.0),
        ("PlanInstalled", pytest.approx(100.015)),
        ("TaskStarted", 120.0),
        ("PlmmChanged", 132.0),  # the output is being written
        ("PlmmChanged", 133.0),  # the raw data leave at the end of the task
        ("TaskEnded", 133.0),
        ("TransferStarted", 150.0),
        ("TransferEnded", 151.0),
        ("PlmmChanged", 151.0),  # the sender frees the output
        ("TransferReceived", pytest.approx(151.015)),
        ("RequestDelivered", pytest.approx(151.015)),
    ]
    levels = [n.level_gb for n in heard if isinstance(n, PlmmChanged)]
    assert levels == [4.0, 5.0, 1.0, 0.0]
    assert next(n for n in heard if isinstance(n, TaskEnded)).completed
    assert next(n for n in heard if isinstance(n, TransferEnded)).completed
    epoch = next(n for n in heard if isinstance(n, EpochPlanned))
    counts = (epoch.new, epoch.accepted, epoch.rejected, epoch.unreachable)
    assert counts == (1, 1, 0, 0)


def test_a_failure_is_published_after_its_violation() -> None:
    heard = run(ScriptedPlanner({"R1": actions(90.0, 150.0)}))
    names = [type(n).__name__ for n in heard]
    assert names[names.index("ViolationRaised") + 1] == "RequestFailed"
    assert "TaskStarted" not in names
    assert [n.level_gb for n in heard if isinstance(n, PlmmChanged)] == [4.0, 0.0]


def test_a_rejection_is_published_with_its_reason() -> None:
    heard = run(ScriptedPlanner())
    rejected = [n for n in heard if isinstance(n, RequestRejected)]
    assert [(n.time, n.reason) for n in rejected] == [(50.0, "not scheduled")]
