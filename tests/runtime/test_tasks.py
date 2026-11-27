"""Tests of the execution of a planned task on SimPy, with exact instants."""

from collections.abc import Generator
from dataclasses import dataclass, field

import pytest
import simpy

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.plan import PlannedTask
from satedge_simulator.domain.requests import TaskSpec
from satedge_simulator.domain.topology import Satellite
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.satellite import SatelliteRuntime
from satedge_simulator.runtime.tasks import run_task

EPS = 1e-4
TASK = PlannedTask("R1", 0, "A", start_s=100.0, end_s=150.0)
OUTPUT = DataKey("R1", 1, "A")
OUTPUT_GB = 1.0  # written at rate 1 Gbps: w_out = 1 s, so the writing starts at 149 s
INPUT_GB = (
    1.0  # read at rate 1 Gbps: 1 s; with 48 s of execution the nominal duration is 50 s
)
SPEC = TaskSpec(execution_s=48.0, output_size_gb=OUTPUT_GB)
INPUT = DataKey("R1", 0, "A")


@dataclass
class Harness:
    env: simpy.Environment
    ledger: DataLedger
    node: SatelliteRuntime
    violations: list[Violation] = field(default_factory=list)
    results: list[bool] = field(default_factory=list)
    ended_at: list[float] = field(default_factory=list)

    def record(self, outcome: bool) -> None:
        self.results.append(outcome)
        self.ended_at.append(self.env.now)

    def start(self, task: PlannedTask = TASK) -> None:
        def process() -> Generator[simpy.Event, object]:
            outcome = yield from run_task(
                self.env,
                task,
                self.node,
                self.ledger,
                self.violations.append,
                EPS,
                SPEC,
                INPUT_GB,
            )
            self.record(outcome)

        self.env.process(process())


def harness(windows: list[Window] | None = None) -> Harness:
    env = simpy.Environment()
    sat = Satellite("A", 100.0, 1.0, WindowSet(windows or [Window(0.0, 1000.0)]))
    return Harness(env, DataLedger(env), SatelliteRuntime(env, sat, EPS))


def input_at(h: Harness, instant: float) -> None:
    def process() -> Generator[simpy.Event, object]:
        yield h.env.timeout(instant)
        h.ledger.mark_complete(DataKey("R1", 0, "A"))

    h.env.process(process())


def test_the_task_runs_at_its_planned_start_and_completes_its_output() -> None:
    h = harness()
    input_at(h, 0.0)
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.violations == []
    assert h.ended_at == [150.0]
    assert h.ledger.is_complete(OUTPUT)


def test_input_arriving_at_the_planned_start_is_in_time() -> None:
    h = harness()
    input_at(h, 100.0)
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.violations == []


def test_input_arriving_within_the_tolerance_is_accepted() -> None:
    h = harness()
    input_at(h, 100.0 + EPS / 2)
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.violations == []


def test_input_arriving_too_late_stops_the_task() -> None:
    h = harness()
    input_at(h, 100.0 + 2 * EPS)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.DATA_NOT_READY]
    assert h.violations[0].at_s == 100.0 + EPS
    assert not h.ledger.is_complete(OUTPUT)


def test_a_busy_hpc_is_a_violation() -> None:
    h = harness()
    input_at(h, 0.0)

    def occupier() -> Generator[simpy.Event, object]:
        request = h.node.hpc.request()
        yield request
        yield h.env.timeout(200.0)
        h.node.hpc.release(request)

    h.env.process(occupier())
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.HPC_BUSY]


def test_an_execution_that_exceeds_its_window_is_stopped_when_the_window_closes() -> (
    None
):
    h = harness(windows=[Window(0.0, 120.0)])
    input_at(h, 0.0)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.HPC_WINDOW]
    assert h.violations[0].at_s == pytest.approx(120.0 + EPS)
    assert h.node.hpc.count == 0
    assert not h.ledger.is_complete(OUTPUT)


def test_a_task_starting_outside_any_window_is_a_violation_at_its_start() -> None:
    h = harness(windows=[Window(0.0, 50.0), Window(200.0, 300.0)])
    input_at(h, 0.0)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.HPC_WINDOW]
    assert h.violations[0].at_s == 100.0
    assert h.node.hpc.count == 0


def test_late_input_within_the_tolerance_shifts_the_whole_execution() -> None:
    h = harness()
    input_at(h, 100.0 + EPS / 2)
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.ended_at == [pytest.approx(150.0 + EPS / 2)]
    assert h.ledger.is_complete(OUTPUT)


def test_the_output_occupies_the_plmm_only_while_it_is_written() -> None:
    h = harness()
    input_at(h, 0.0)
    levels: dict[float, float] = {}

    def probe(instant: float) -> Generator[simpy.Event, object]:
        yield h.env.timeout(instant)
        levels[instant] = h.node.plmm.level_gb

    for instant in (148.5, 149.5):
        h.env.process(probe(instant))
    h.start()
    h.env.run()
    assert levels == {148.5: 0.0, 149.5: OUTPUT_GB}


def test_the_input_is_freed_from_the_plmm_at_the_end_of_the_task() -> None:
    h = harness()
    input_at(h, 0.0)

    def store_input() -> Generator[simpy.Event, object]:
        yield from h.node.plmm.reserve(h.env, INPUT, 5.0, EPS)

    h.env.process(store_input())
    h.start()
    h.env.run()
    assert h.results == [True]
    assert h.node.plmm.occupied_gb(INPUT) == 0.0
    assert h.node.plmm.level_gb == pytest.approx(OUTPUT_GB)


def test_a_full_plmm_when_writing_the_output_is_a_violation() -> None:
    h = harness()
    input_at(h, 0.0)

    def fill() -> Generator[simpy.Event, object]:
        yield from h.node.plmm.reserve(h.env, DataKey("X", 0, "A"), 100.0, EPS)

    h.env.process(fill())
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.PLMM_FULL]
    assert h.violations[0].at_s == pytest.approx(149.0 + EPS)
    assert not h.ledger.is_complete(OUTPUT)


def test_the_duration_comes_from_the_domain_not_from_the_plan() -> None:
    h = harness()
    input_at(h, 0.0)
    slower = TaskSpec(execution_s=58.0, output_size_gb=OUTPUT_GB)

    def process() -> Generator[simpy.Event, object]:
        outcome = yield from run_task(
            h.env, TASK, h.node, h.ledger, h.violations.append, EPS, slower, INPUT_GB
        )
        h.record(outcome)

    h.env.process(process())
    h.env.run()
    assert h.results == [True]
    assert h.ended_at == [pytest.approx(100.0 + INPUT_GB + 58.0 + OUTPUT_GB)]
    assert h.ledger.is_complete(OUTPUT)


def hold_plmm_until(h: Harness, instant: float) -> None:
    """Fill the whole PLMM at 0 s and free it at ``instant``."""
    filler = DataKey("X", 0, "A")

    def process() -> Generator[simpy.Event, object]:
        yield from h.node.plmm.reserve(h.env, filler, 100.0, EPS)
        yield h.env.timeout(instant)
        h.node.plmm.release(filler)

    h.env.process(process())


def test_delays_that_add_up_past_the_window_stop_the_execution() -> None:
    # Each delay is within the tolerance: the input arrives 0.75 eps late, the PLMM frees up
    # 0.5 eps after the writing should start. Together they push the end 1.25 eps past the
    # window, which a check at the start could not see.
    h = harness(windows=[Window(0.0, 150.0)])
    input_at(h, 100.0 + 0.75 * EPS)
    hold_plmm_until(h, 149.0 + 1.25 * EPS)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.HPC_WINDOW]
    assert h.violations[0].at_s == pytest.approx(150.0 + EPS)
    assert h.node.plmm.occupied_gb(OUTPUT) == 0.0
    assert h.node.plmm.level_gb == 0.0
    assert h.node.hpc.count == 0
    assert not h.ledger.is_complete(OUTPUT)


def test_a_closing_while_waiting_for_the_plmm_cancels_the_reservation() -> None:
    # The window closes at 149 + eps / 2, while the output waits for the PLMM (from 149 s).
    h = harness(windows=[Window(0.0, 149.0 - EPS / 2)])
    input_at(h, 0.0)
    hold_plmm_until(h, 200.0)
    h.start()
    h.env.run()
    assert h.results == [False]
    assert [v.kind for v in h.violations] == [ViolationKind.HPC_WINDOW]
    assert h.violations[0].at_s == pytest.approx(149.0 + EPS / 2)
    assert h.node.plmm.level_gb == 0.0  # the cancelled reservation never took the space


def test_an_execution_ending_exactly_when_the_window_closes_is_in_time() -> None:
    # A tolerance exact in binary makes the end and the closing the very same float: 150 s.
    tolerance = 0.25
    env = simpy.Environment()
    sat = Satellite("A", 100.0, 1.0, WindowSet([Window(0.0, 150.0 - tolerance)]))
    h = Harness(env, DataLedger(env), SatelliteRuntime(env, sat, tolerance))
    input_at(h, 0.0)

    def process() -> Generator[simpy.Event, object]:
        outcome = yield from run_task(
            env, TASK, h.node, h.ledger, h.violations.append, tolerance, SPEC, INPUT_GB
        )
        h.record(outcome)

    env.process(process())
    env.run()
    assert h.results == [True]
    assert h.violations == []
    assert h.ledger.is_complete(OUTPUT)
