"""A command of the command line (Command): its arguments and what it does."""

from __future__ import annotations

import argparse
from typing import Protocol, TextIO


class Command(Protocol):
    """One sub-command: it declares its arguments and runs on the parsed ones."""

    name: str
    help: str

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add the arguments of the command to its parser."""
        ...

    def execute(self, args: argparse.Namespace, out: TextIO) -> None:
        """Run the command and report to ``out``.

        Raises:
            SimulatorError: If the command cannot run; the message is for the user.
        """
        ...
