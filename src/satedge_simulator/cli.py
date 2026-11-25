"""Command line of the simulator. The messages for the user are in Italian."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any, NoReturn, TextIO

from satedge_simulator.api import (
    EVENTS_FILE,
    METRICS_FILE,
    SimulationResult,
    simulate_file,
)
from satedge_simulator.errors import SimulatorError
from satedge_simulator.texts import PRIORITY_CLASSES, VIOLATIONS


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


class _Formatter(argparse.HelpFormatter):
    """Writes the usage line with an Italian prefix."""

    def add_usage(self, usage, actions, groups, prefix=None):  # type: ignore[no-untyped-def]
        super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


class _Parser(argparse.ArgumentParser):
    """An argument parser whose help and errors are in Italian."""

    _ERRORS = (
        (
            "the following arguments are required: ",
            "mancano gli argomenti obbligatori: ",
        ),
        ("unrecognized arguments: ", "argomenti non riconosciuti: "),
        ("invalid choice: ", "scelta non valida: "),
        ("expected one argument", "serve un valore"),
        ("argument ", "argomento "),
        ("(choose from ", "(valori possibili: "),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("formatter_class", _Formatter)
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "argomenti"
        self._optionals.title = "opzioni"
        self.add_argument(
            "-h", "--help", action="help", help="mostra questo aiuto ed esce"
        )

    def error(self, message: str) -> NoReturn:
        for english, italian in self._ERRORS:
            message = message.replace(english, italian)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: errore: {message}\n")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="satedge-simulator",
        description="Simulatore a eventi discreti della costellazione satellitare edge.",
    )
    commands = parser.add_subparsers(
        title="comandi", dest="command", metavar="comando", required=True
    )
    run = commands.add_parser(
        "run", help="esegue uno scenario pianificato da satedge-workflow-scheduler"
    )
    run.add_argument("scenario", help="file YAML dello scenario")
    run.add_argument(
        "-o",
        "--output",
        metavar="CARTELLA",
        help=f"cartella dei risultati ({EVENTS_FILE} e {METRICS_FILE})",
    )
    return parser


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
