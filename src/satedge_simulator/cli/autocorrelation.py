"""The command ``autocorrelation``: how correlated the requests that follow one another are."""

from __future__ import annotations

import argparse
from typing import TextIO

from satedge_simulator.api import autocorrelation_file
from satedge_simulator.cli.batch import CORRELATED
from satedge_simulator.texts import STATISTICS


class AutocorrelationCommand:
    """Runs one long run and measures the autocorrelation of the per-request statistics."""

    name = "autocorrelation"
    help = "autocorrelazione delle statistiche per richiesta, per scegliere i batch"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "scenario", help="file YAML dello scenario, con una fine lontana"
        )
        parser.add_argument(
            "--warmup",
            type=float,
            required=True,
            metavar="SECONDI",
            help="riscaldamento da scartare, stimato con il transitorio",
        )
        parser.add_argument(
            "--max-lag",
            type=int,
            default=50,
            metavar="LAG",
            help="lag massimo (default 50)",
        )
        parser.add_argument(
            "-o",
            "--output",
            metavar="CARTELLA",
            help="cartella dei risultati (autocorrelation.json e autocorrelation.csv)",
        )

    def execute(self, args: argparse.Namespace, out: TextIO) -> None:
        report = autocorrelation_file(
            args.scenario, args.warmup, args.max_lag, args.output
        )
        print(
            f"Autocorrelazione dopo {report.warmup_s:g} s di riscaldamento, fino al lag "
            f"{report.max_lag}.",
            file=out,
        )
        for statistic, values in report.autocorrelation.items():
            count = report.observations[statistic]
            if not values:
                print(
                    f"  {STATISTICS[statistic]}: {count} osservazioni, troppo poche",
                    file=out,
                )
                continue
            fades = next(
                (j for j, r in enumerate(values, start=1) if abs(r) < CORRELATED), None
            )
            where = (
                f"sotto {CORRELATED} dal lag {fades}"
                if fades
                else f"sopra {CORRELATED} fino al lag massimo"
            )
            print(
                f"  {STATISTICS[statistic]}: {count} osservazioni, lag 1 = {values[0]:.3f}, {where}",
                file=out,
            )
        if args.output is not None:
            print(f"Autocorrelazione in {args.output}.", file=out)
