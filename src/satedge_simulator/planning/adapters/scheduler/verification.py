"""Cross-check of the as-run calendar with the feasibility checker of the scheduler.

The check covers what the simulator delivered: for each epoch, the requests accepted in it and
delivered, with the release and the plan arrival that epoch saw, against the as-run of the
requests delivered from earlier epochs, which play the committed calendar. A clean result
means that what the simulator delivered respects the final model. Failed requests, raw data of
requests that were never served, and the real occupation of the PLMMs are outside it: the
metrics and the violations of the run measure them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from satedge_workflow_scheduler.domain.solution import (
    RequestOutcome,
    Schedule,
    Solution,
    SolveStatus,
)
from satedge_workflow_scheduler.scheduling.deadline import DeadlineMode
from satedge_workflow_scheduler.scheduling.feasibility import Constraint, check

from satedge_simulator.domain.lifecycle import RequestRecord, RequestStatus
from satedge_simulator.domain.requests import RequestSpec
from satedge_simulator.domain.topology import Constellation
from satedge_simulator.metrics.as_run import AsRun
from satedge_simulator.planning.adapters.scheduler.to_instance import (
    execution_of,
    to_instance,
    transfer_of,
)
from satedge_simulator.planning.epochs import Epoch
from satedge_simulator.planning.ports import (
    Commitment,
    PlanningDecision,
    PlanningSnapshot,
)
from satedge_simulator.planning.propagation import plan_arrival_times
from satedge_simulator.planning.rolling_planner import released_at

_DELIVERED = frozenset({RequestStatus.DELIVERED_ON_TIME, RequestStatus.DELIVERED_LATE})


@dataclass(frozen=True, slots=True)
class AsRunFinding:
    """A constraint of the final model that the as-run calendar does not respect.

    Attributes:
        epoch: The epoch whose delivered requests were checked.
        constraint: The family of the constraint, with its numbers in the model, in Italian.
        request_id: The request concerned, if the finding concerns one.
        message: What is wrong, with the values involved.
    """

    epoch: int
    constraint: str
    request_id: str | None
    message: str


def verify_as_run(
    constellation: Constellation,
    requests: Iterable[RequestSpec],
    records: Mapping[str, RequestRecord],
    decisions: Iterable[tuple[Epoch, PlanningDecision]],
    as_run: AsRun,
    horizon_s: float,
    hard_deadlines: bool = True,
    tolerance_s: float = 1e-6,
) -> tuple[AsRunFinding, ...]:
    """Check the delivered requests of each epoch against the final model.

    Args:
        constellation: The network of the simulation.
        requests: The requests of the scenario.
        records: The final record of each request.
        decisions: The decision of each epoch, in order.
        as_run: What was executed.
        horizon_s: The horizon of the instances, as given to the planner.
        hard_deadlines: Whether the deadlines are hard, as for the planner.
        tolerance_s: Tolerance of the comparisons between instants and sizes.

    Returns:
        The findings, each once, in the first epoch that shows it; empty if the delivered
        requests respect the model.
    """
    specs = {r.id: r for r in requests}
    delivered = {i for i, r in records.items() if r.status in _DELIVERED}
    mode = DeadlineMode.HARD if hard_deadlines else DeadlineMode.SOFT
    earlier: list[
        RequestSpec
    ] = []  # delivered, accepted in earlier epochs, as accepted
    findings: list[AsRunFinding] = []
    for epoch, decision in decisions:
        accepted = {t.request_id for t in decision.plan.tasks} | {
            t.request_id for t in decision.plan.transfers
        }
        new = [
            released_at(specs[i], epoch.start_s)
            for i in specs
            if i in accepted and i in delivered
        ]
        if new:
            found = _check_epoch(
                constellation,
                epoch,
                new,
                earlier,
                records,
                as_run,
                horizon_s,
                mode,
                tolerance_s,
            )
            # the requests of earlier epochs are checked again as committed: keep each
            # finding once, in the first epoch that shows it
            findings += [
                f for f in found if _what(f) not in {_what(g) for g in findings}
            ]
        earlier += new
    return tuple(findings)


def _what(finding: AsRunFinding) -> tuple[str, str | None, str]:
    return (finding.constraint, finding.request_id, finding.message)


def _check_epoch(
    constellation: Constellation,
    epoch: Epoch,
    new: list[RequestSpec],
    earlier: list[RequestSpec],
    records: Mapping[str, RequestRecord],
    as_run: AsRun,
    horizon_s: float,
    mode: DeadlineMode,
    tolerance_s: float,
) -> list[AsRunFinding]:
    commitments = tuple(
        Commitment(
            request=r,
            tasks=as_run.of_requests({r.id}).tasks,
            transfers=as_run.of_requests({r.id}).transfers,
        )
        for r in earlier
    )
    snapshot = PlanningSnapshot(
        epoch=epoch,
        constellation=constellation,
        new_requests=tuple(new),
        commitments=commitments,
        plan_arrival_s=plan_arrival_times(constellation, epoch.ready_s),
    )
    instance = to_instance(snapshot, horizon_s)
    executed = as_run.of_requests({r.id for r in (*earlier, *new)})
    solution = Solution(
        schedule=Schedule(
            executions=tuple(execution_of(t) for t in executed.tasks),
            transfers=tuple(transfer_of(t) for t in executed.transfers),
        ),
        outcomes=tuple(
            RequestOutcome(
                r.id, accepted=True, delivery_time=records[r.id].history[-1][0]
            )
            for r in (*earlier, *new)
        ),
        status=SolveStatus.FEASIBLE,
    )
    return [
        AsRunFinding(
            epoch.index,
            _CONSTRAINTS.get(v.constraint, str(v.constraint)),
            v.request_id,
            v.message,
        )
        for v in check(instance, solution, mode, tolerance_s)
    ]


_CONSTRAINTS = {
    Constraint.OUTCOMES: "esiti: uno per richiesta, nessun rifiuto con scadenze soft",
    Constraint.ASSIGNMENT: "(2) assegnazione: un'esecuzione per task, su un satellite",
    Constraint.TASK_DURATION: "durata del task: il task dura L̄_{i,s}",
    Constraint.PRECEDENCE: "(3) precedenza",
    Constraint.RELEASE: "(4) rilascio del raw",
    Constraint.COMPUTING_WINDOW: "(5)-(7) finestra di calcolo",
    Constraint.HPC_OVERLAP: "(8)-(10) un task alla volta sull'HPC",
    Constraint.PATH: "(11)-(13) percorso del dato",
    Constraint.TRANSMISSION_TIME: "tempo di trasmissione: il trasferimento dura D_{a,e}",
    Constraint.AFTER_PRODUCER: "(14a) trasmissione dopo il produttore",
    Constraint.AFTER_RELEASE: "(14b) raw inviato dopo il rilascio",
    Constraint.STORE_AND_FORWARD: "(15) store-and-forward",
    Constraint.ARRIVAL: "(16a) consumatore dopo l'arrivo del dato",
    Constraint.LIMIT: "(16b) consegna entro il limite di tempo",
    Constraint.DELIVERY_TIME: "(28) istante di consegna",
    Constraint.VISIBILITY_WINDOW: "(17a)-(17c) finestra di visibilità",
    Constraint.LINK_CONTENTION: "(18)-(19) una trasmissione alla volta sull'arco",
    Constraint.PLMM_CAPACITY: "(20)-(27) capacità della PLMM",
    Constraint.COMMITTED: "online: calendario impegnato invariato",
    Constraint.OBJECTIVE: "obiettivo: il valore riportato è quello del calendario",
    Constraint.PLAN_RELEASE: "(30)-(31) rilascio del piano",
}
"""The name of each family of constraints, in Italian. The details of a finding keep the
message of the scheduler."""
