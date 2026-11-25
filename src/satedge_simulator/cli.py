"""Command line of the simulator. The messages for the user are in Italian."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TextIO

from satedge_simulator.api import (
    EVENTS_FILE,
    METRICS_FILE,
    SimulationResult,
    simulate_file,
)
from satedge_simulator.domain.workload import Priority
from satedge_simulator.errors import SimulatorError

_CLASS_NAMES = {Priority.URGENT: "urgenti", Priority.NON_URGENT: "non urgenti"}


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    """Run the command line with ``argv``, and return the exit code.

    The code is 0 when the simulation ran, 1 when it could not run, 2 when the arguments are
    wrong.
    """
    stdout = out or sys.stdout
    args = _parser().parse_args(argv)
    try:
        result = simulate_file(args.scenario, args.output)
    except SimulatorError as error:
        print(f"errore: {error}", file=sys.stderr)
        return 1
    _report(result, args.output, stdout)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="satedge-simulator",
        description="Simulatore a eventi discreti della costellazione satellitare edge.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser(
        "run", help="esegue uno scenario pianificato da satedge-workflow-scheduler"
    )
    run.add_argument("scenario", help="file YAML dello scenario")
    run.add_argument(
        "-o",
        "--output",
        help=f"cartella dei risultati ({EVENTS_FILE} e {METRICS_FILE})",
    )
    return parser


def _report(result: SimulationResult, output: str | None, out: TextIO) -> None:
    outcome = result.outcome
    metrics = outcome.metrics
    print(f"Simulazione conclusa a {outcome.end_s:g} s.", file=out)
    for c in metrics.requests:
        print(
            f"Richieste {_CLASS_NAMES[c.priority]}: {c.arrived} arrivate, "
            f"{c.accepted} accettate, {c.rejected} rifiutate; "
            f"{c.delivered_on_time} consegnate in tempo, {c.delivered_late} in ritardo, "
            f"{c.failed} fallite, {c.unfinished} non concluse.",
            file=out,
        )
    if metrics.violations:
        kinds = ", ".join(f"{k.value} {n}" for k, n in metrics.violations.items())
        print(f"Violazioni del piano: {kinds}.", file=out)
    else:
        print("Violazioni del piano: nessuna.", file=out)
    if metrics.lost_raw:
        print(f"Dati raw persi per PLMM piena: {metrics.lost_raw}.", file=out)
    if result.verified:
        print("Verifica dell'esecuzione con il modello: superata.", file=out)
    else:
        print(
            f"Verifica dell'esecuzione con il modello: {len(result.findings)} vincoli "
            "non rispettati.",
            file=out,
        )
        for f in result.findings:
            who = f"{f.request_id}: " if f.request_id else ""
            print(f"  epoca {f.epoch}, {f.constraint}: {who}{f.message}", file=out)
    if output is not None:
        print(f"Risultati in {output}.", file=out)
