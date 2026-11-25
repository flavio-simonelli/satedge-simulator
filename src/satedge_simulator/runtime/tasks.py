"""Execution of one planned task on the HPC of its satellite."""

from __future__ import annotations

from collections.abc import Callable, Generator

import simpy

from satedge_simulator.domain.plan import PlannedTask
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.domain.workload import TaskSpec
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.satellite import SatelliteRuntime
from satedge_simulator.runtime.timing import guarded_request, guarded_wait

Report = Callable[[Violation], None]


def run_task(
    env: simpy.Environment,
    task: PlannedTask,
    node: SatelliteRuntime,
    ledger: DataLedger,
    report: Report,
    tolerance_s: float,
    spec: TaskSpec,
    input_size_gb: float,
) -> Generator[simpy.Event, object, bool]:
    """Run ``task`` at its planned start, if its preconditions hold.

    The plan only decides the start. Durations and sizes come from the domain (``spec`` and
    ``input_size_gb``), so the execution does not depend on the nominal values of the plan.

    The preconditions are: the input is complete on the satellite and the HPC is free. Each wait
    is bounded by ``tolerance_s``; a precondition that does not hold in time is reported as a
    violation, and the task does not run. If the input arrives late, within the tolerance, the
    whole execution is shifted by the same delay. The execution must end before its computing
    window closes, tolerance included, or it is stopped with a violation.

    Returns:
        ``True`` if the task ran to its end, ``False`` if a violation stopped it.
    """
    yield env.timeout(task.start_s - env.now)
    if not (yield from await_input(env, task, node, ledger, tolerance_s)):
        report(_violation(env, task, ViolationKind.DATA_NOT_READY))
        return False
    request = node.hpc.request()
    if not (yield from guarded_request(env, request, tolerance_s)):
        report(_violation(env, task, ViolationKind.HPC_BUSY))
        return False
    try:
        return (
            yield from _execute(
                env, task, node, ledger, report, tolerance_s, spec, input_size_gb
            )
        )
    finally:
        node.hpc.release(request)


def _execute(
    env: simpy.Environment,
    task: PlannedTask,
    node: SatelliteRuntime,
    ledger: DataLedger,
    report: Report,
    tolerance_s: float,
    spec: TaskSpec,
    input_size_gb: float,
) -> Generator[simpy.Event, object, bool]:
    """Run the HPC occupation against the closing of its computing window.

    The occupation runs as its own process and races the closing of the window (a watchdog): any
    delay, wherever it builds up, that pushes the end past the window stops the execution with a
    violation. The occupation must start inside a window.
    """
    closing = node.window_closing()
    if closing is None:
        report(_violation(env, task, ViolationKind.HPC_WINDOW))
        return False
    work = env.process(
        _occupy(env, task, node, ledger, report, tolerance_s, spec, input_size_gb)
    )
    yield work | closing
    if not work.triggered:
        work.interrupt()
        report(_violation(env, task, ViolationKind.HPC_WINDOW))
        return False
    return work.value is True


def _occupy(
    env: simpy.Environment,
    task: PlannedTask,
    node: SatelliteRuntime,
    ledger: DataLedger,
    report: Report,
    tolerance_s: float,
    spec: TaskSpec,
    input_size_gb: float,
) -> Generator[simpy.Event, object, bool]:
    """Read the input, execute, write the output: durations and sizes from the domain.

    The output occupies the PLMM only while it is written, the last ``w_out`` seconds; the input
    is freed when the occupation ends. If the window closes first, the occupation is interrupted
    and frees the output it reserved.
    """
    satellite = node.satellite
    read_s = satellite.hpc_io_time(input_size_gb)
    write_s = satellite.hpc_io_time(spec.output_size_gb)
    output = DataKey(task.request_id, task.task_index + 1, node.node_id)
    try:
        yield env.timeout(read_s + spec.execution_s)
        if not (
            yield from node.plmm.reserve(env, output, spec.output_size_gb, tolerance_s)
        ):
            report(_violation(env, task, ViolationKind.PLMM_FULL))
            return False
        yield env.timeout(write_s)
    except simpy.Interrupt:
        node.plmm.release(output)
        return False
    node.plmm.release(DataKey(task.request_id, task.task_index, node.node_id))
    ledger.mark_complete(output)
    return True


def await_input(
    env: simpy.Environment,
    task: PlannedTask,
    node: SatelliteRuntime,
    ledger: DataLedger,
    tolerance_s: float,
) -> Generator[simpy.Event, object, bool]:
    """Wait, within the tolerance, for the input of ``task`` on its satellite."""
    key = DataKey(task.request_id, task.task_index, node.node_id)
    return (yield from guarded_wait(env, ledger.complete_event(key), tolerance_s))


def _violation(
    env: simpy.Environment, task: PlannedTask, kind: ViolationKind
) -> Violation:
    return Violation(env.now, kind, task.request_id, task.satellite)
