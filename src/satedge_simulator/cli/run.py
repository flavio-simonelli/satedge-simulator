"""The command ``run``: one simulation of a scenario, checked against the model."""

from __future__ import annotations

import argparse
from typing import TextIO

from satedge_simulator.api import (
    EVENTS_FILE,
    METRICS_FILE,
    SimulationResult,
    simulate_file,
)
from satedge_simulator.texts import PRIORITY_CLASSES, VIOLATIONS


class RunCommand:
    """Runs a scenario planned by satedge-workflow-scheduler and reports its outcome."""

    name = "run"
    help = "esegue uno scenario pianificato da satedge-workflow-scheduler"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("scenario", help="file YAML dello scenario")
        parser.add_argument(
            "-o",
            "--output",
            metavar="CARTELLA",
            help=f"cartella dei risultati ({EVENTS_FILE} e {METRICS_FILE})",
        )

    def execute(self, args: argparse.Namespace, out: TextIO) -> None:
        _report(simulate_file(args.scenario, args.output), args.output, out)


def _report(result: SimulationResult, output: str | None, out: TextIO) -> None:
    outcome = result.outcome
    metrics = outcome.metrics
    print(f"Simulazione conclusa a {outcome.end_s:g} s.", file=out)
    for c in metrics.requests:
        print(
            f"Richieste {PRIORITY_CLASSES[c.priority]}: {c.arrived} arrivate, "
            f"{c.accepted} accettate, {c.rejected} rifiutate; "
            f"{c.delivered_on_time} consegnate in tempo, {c.delivered_late} in ritardo, "
            f"{c.failed} fallite, {c.unfinished} non concluse.",
            file=out,
        )
    if metrics.violations:
        kinds = ", ".join(f"{VIOLATIONS[k]} {n}" for k, n in metrics.violations.items())
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
