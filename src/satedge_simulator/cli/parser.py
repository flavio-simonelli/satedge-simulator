"""An argument parser that speaks Italian: usage, help and errors."""

from __future__ import annotations

import argparse
import sys
from typing import Any, NoReturn


class ItalianFormatter(argparse.HelpFormatter):
    """Writes the usage line with an Italian prefix."""

    def add_usage(self, usage, actions, groups, prefix=None):  # type: ignore[no-untyped-def]
        super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


class ItalianParser(argparse.ArgumentParser):
    """An argument parser whose help and errors are in Italian."""

    _ERRORS = (
        (
            "the following arguments are required: ",
            "mancano gli argomenti obbligatori: ",
        ),
        ("unrecognized arguments: ", "argomenti non riconosciuti: "),
        ("invalid choice: ", "scelta non valida: "),
        ("invalid int value: ", "non è un numero intero: "),
        ("invalid float value: ", "non è un numero: "),
        ("expected one argument", "serve un valore"),
        ("argument ", "argomento "),
        ("(choose from ", "(valori possibili: "),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("formatter_class", ItalianFormatter)
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
