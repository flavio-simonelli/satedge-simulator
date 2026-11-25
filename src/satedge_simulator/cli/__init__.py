"""Command line of the simulator. The messages for the user are in Italian.

Each sub-command is a :class:`~satedge_simulator.cli.command.Command`; ``main`` builds the
parser from them and runs the one chosen.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from satedge_simulator.cli.autocorrelation import AutocorrelationCommand
from satedge_simulator.cli.batch import BatchCommand
from satedge_simulator.cli.command import Command
from satedge_simulator.cli.parser import ItalianParser
from satedge_simulator.cli.replicate import ReplicateCommand
from satedge_simulator.cli.run import RunCommand
from satedge_simulator.errors import SimulatorError

COMMANDS: tuple[Command, ...] = (
    RunCommand(),
    ReplicateCommand(),
    BatchCommand(),
    AutocorrelationCommand(),
)
"""The sub-commands, in the order the help lists them."""


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    """Run the command line with ``argv``, and return the exit code.

    The code is 0 when the command ran, 1 when it could not run, 2 when the arguments are
    wrong.
    """
    parser = ItalianParser(
        prog="satedge-simulator",
        description="Simulatore a eventi discreti della costellazione satellitare edge.",
    )
    sub = parser.add_subparsers(
        title="comandi", dest="command", metavar="comando", required=True
    )
    by_name: dict[str, Command] = {}
    for command in COMMANDS:
        command.configure(sub.add_parser(command.name, help=command.help))
        by_name[command.name] = command
    args = parser.parse_args(argv)
    try:
        by_name[args.command].execute(args, out or sys.stdout)
    except SimulatorError as error:
        print(f"errore: {error}", file=sys.stderr)
        return 1
    return 0


__all__ = ["COMMANDS", "main"]
