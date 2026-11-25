"""Execution of one planned transfer on one direction of a link."""

from __future__ import annotations

from collections.abc import Callable, Generator

import simpy
from simpy.resources.resource import Request

from satedge_simulator.domain.plan import PlannedTransfer
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.domain.violations import Violation, ViolationKind
from satedge_simulator.runtime.ledger import DataKey, DataLedger
from satedge_simulator.runtime.links import LinkRuntime
from satedge_simulator.runtime.satellite import SatelliteRuntime
from satedge_simulator.runtime.timing import guarded_request, guarded_wait

Report = Callable[[Violation], None]


def run_transfer(
    env: simpy.Environment,
    transfer: PlannedTransfer,
    link: LinkRuntime,
    sender: SatelliteRuntime,
    receiver: SatelliteRuntime | None,
    ledger: DataLedger,
    report: Report,
    tolerance_s: float,
    size_gb: float,
) -> Generator[simpy.Event, object, bool]:
    """Send a data item on ``link`` at its planned start, if its preconditions hold.

    The plan only decides the start. The transmission time and the latency come from the link,
    the size from the domain. With ``ξ`` the actual start, ``D`` the transmission time and ``λ``
    the latency:

    - the channel is held during ``[ξ, ξ + D]``, and the sender frees its copy at ``ξ + D``;
    - the receiver's PLMM holds the item from ``ξ + λ``, when the first bits arrive;
    - the item is complete on the receiver at ``ξ + D + λ``;
    - the whole span ``[ξ, ξ + D + λ]`` must lie in a visibility window: if the window closes
      before the last bits arrive, the transfer fails.

    ``receiver`` is ``None`` when the target is the ground station: it has no PLMM, and the item
    complete there is the delivery.

    The preconditions are: the item is complete on the sender and the channel is free. Each wait
    is bounded by ``tolerance_s``; a late start, within the tolerance, shifts the whole transfer.

    Returns:
        ``True`` if the item is complete on the receiver, ``False`` if a violation stopped it.
    """
    yield env.timeout(transfer.start_s - env.now)
    sent = DataKey(transfer.request_id, transfer.data_index, transfer.source)
    if not (yield from guarded_wait(env, ledger.complete_event(sent), tolerance_s)):
        report(_violation(env, transfer, ViolationKind.DATA_NOT_READY, transfer.source))
        return False
    request = link.channel.request()
    if not (yield from guarded_request(env, request, tolerance_s)):
        report(_violation(env, transfer, ViolationKind.LINK_BUSY, transfer.source))
        return False
    closing = link.window_closing()
    if closing is None:
        link.channel.release(request)
        report(_violation(env, transfer, ViolationKind.LINK_WINDOW, transfer.source))
        return False
    sending = env.process(_send(env, link, request, sender, sent, size_gb))
    reception = env.process(
        _receive(env, transfer, link, receiver, ledger, report, tolerance_s, size_gb)
    )
    yield reception | closing
    if not reception.triggered:
        if sending.is_alive:
            sending.interrupt()
        reception.interrupt()
        report(_violation(env, transfer, ViolationKind.LINK_WINDOW, transfer.source))
        return False
    return reception.value is True


def _send(
    env: simpy.Environment,
    link: LinkRuntime,
    request: Request,
    sender: SatelliteRuntime,
    sent: DataKey,
    size_gb: float,
) -> Generator[simpy.Event, object]:
    """Hold the channel for the transmission, then free it and the sender's copy.

    If the window closes first, the channel is freed and the sender keeps its copy.
    """
    try:
        yield env.timeout(link.link.transmission_time(size_gb))
    except simpy.Interrupt:
        return
    finally:
        link.channel.release(request)
    sender.plmm.release(sent)


def _receive(
    env: simpy.Environment,
    transfer: PlannedTransfer,
    link: LinkRuntime,
    receiver: SatelliteRuntime | None,
    ledger: DataLedger,
    report: Report,
    tolerance_s: float,
    size_gb: float,
) -> Generator[simpy.Event, object, bool]:
    """Store the item on the receiver from the first bits, and complete it at the last ones.

    If the window closes first, the reception frees what it reserved.
    """
    received = DataKey(transfer.request_id, transfer.data_index, transfer.target)
    complete_at = env.now + link.link.transmission_time(size_gb) + link.link.latency_s
    try:
        yield env.timeout(link.link.latency_s)
        if receiver is not None and not (
            yield from receiver.plmm.reserve(env, received, size_gb, tolerance_s)
        ):
            report(_violation(env, transfer, ViolationKind.PLMM_FULL, transfer.target))
            return False
        # The arrival does not shift by the wait for the PLMM, unlike the output of a task: the
        # sender sets when the bits arrive, and the receiver cannot slow them down. A wait is
        # accepted only within the tolerance, the same one that covers simultaneous events.
        yield env.timeout(max(0.0, complete_at - env.now))
    except simpy.Interrupt:
        if receiver is not None:
            receiver.plmm.release(received)
        return False
    ledger.mark_complete(received)
    return True


def _violation(
    env: simpy.Environment,
    transfer: PlannedTransfer,
    kind: ViolationKind,
    node: NodeId,
) -> Violation:
    return Violation(env.now, kind, transfer.request_id, node)
