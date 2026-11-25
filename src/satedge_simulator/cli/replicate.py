"""The command ``replicate``: the finite-horizon study, with its transient."""

from __future__ import annotations

import argparse
from typing import TextIO

from satedge_simulator.api import replicate_file
from satedge_simulator.cli.formatting import interval
from satedge_simulator.domain.topology import ORBITAL_PERIOD_S
from satedge_simulator.texts import STATISTICS


class ReplicateCommand:
    """Runs independent replications and estimates each statistic over the horizon."""

    name = "replicate"
    help = "orizzonte finito: repliche indipendenti, intervalli di confidenza e transitorio"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("scenario", help="file YAML dello scenario")
        parser.add_argument(
            "-n",
            "--replications",
            type=int,
            default=30,
            metavar="N",
            help="numero di repliche (default 30)",
        )
        parser.add_argument(
            "--cell",
            type=float,
            default=ORBITAL_PERIOD_S / 2,
            metavar="SECONDI",
            help="ampiezza delle celle del transitorio (default mezzo periodo orbitale)",
        )
        parser.add_argument(
            "--welch",
            type=int,
            default=2,
            metavar="CELLE",
            help="semiampiezza della media mobile di Welch, in celle (default 2)",
        )
        parser.add_argument(
            "--level",
            type=float,
            default=0.95,
            metavar="LIVELLO",
            help="livello di confidenza (default 0.95)",
        )
        parser.add_argument(
            "-o",
            "--output",
            metavar="CARTELLA",
            help="cartella dei risultati (replications.json e transient.csv)",
        )

    def execute(self, args: argparse.Namespace, out: TextIO) -> None:
        report = replicate_file(
            args.scenario,
            args.replications,
            args.cell,
            args.welch,
            args.level,
            args.output,
        )
        print(
            f"Orizzonte finito: {report.replications} repliche dal seed {report.seed}, "
            f"intervalli al {report.level:.0%}.",
            file=out,
        )
        for statistic, estimate in report.estimates.items():
            print(
                f"  {STATISTICS[statistic]}: {interval(estimate, 'repliche')}", file=out
            )
        if args.output is not None:
            print(f"Stime e transitorio in {args.output}.", file=out)
