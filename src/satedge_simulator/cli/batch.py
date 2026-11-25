"""The command ``batch``: the infinite-horizon study, by batch means."""

from __future__ import annotations

import argparse
from typing import TextIO

from satedge_simulator.api import batch_means_file
from satedge_simulator.cli.formatting import interval
from satedge_simulator.domain.topology import ORBITAL_PERIOD_S
from satedge_simulator.texts import STATISTICS

CORRELATED = 0.2
"""Above this lag-1 autocorrelation the batch means cannot be taken as independent."""


class BatchCommand:
    """Runs one long run and estimates each statistic by batch means."""

    name = "batch"
    help = "orizzonte infinito: batch means su una run lunga"

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
            "-b",
            "--batch-size",
            type=int,
            default=32,
            metavar="RICHIESTE",
            help="richieste per batch, per le statistiche per richiesta (default 32)",
        )
        parser.add_argument(
            "--batch-duration",
            type=float,
            default=ORBITAL_PERIOD_S,
            metavar="SECONDI",
            help="durata dei batch per le statistiche nel tempo, meglio un multiplo del "
            "periodo orbitale (default un periodo)",
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
            help="cartella dei risultati (batch_means.json e batches.csv)",
        )

    def execute(self, args: argparse.Namespace, out: TextIO) -> None:
        report = batch_means_file(
            args.scenario,
            args.warmup,
            args.batch_size,
            args.batch_duration,
            args.level,
            args.output,
        )
        print(
            f"Orizzonte infinito: run fino a {report.end_s:g} s, riscaldamento {report.warmup_s:g} s, "
            f"batch di {report.batch_size} richieste o {report.batch_duration_s:g} s, "
            f"intervalli al {report.level:.0%}.",
            file=out,
        )
        for statistic, batches in report.results.items():
            line = f"  {STATISTICS[statistic]}: {interval(batches.interval, 'batch')}"
            if batches.lag1 is not None:
                line += f", autocorrelazione dei batch {batches.lag1:.3f}"
                if abs(batches.lag1) > CORRELATED:
                    line += " (troppo alta: allungare i batch)"
            print(line, file=out)
        if args.output is not None:
            print(f"Stime e batch in {args.output}.", file=out)
