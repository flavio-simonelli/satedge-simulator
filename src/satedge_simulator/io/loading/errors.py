"""Errors of the mapper: a rule of the domain broken by a value, reported with its file."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from satedge_simulator.errors import DocumentError, DomainError


@contextmanager
def errors_in(file: Path, what: str) -> Iterator[None]:
    """Report a :class:`DomainError` raised in the block as an error of ``file``.

    Args:
        file: The file that holds the values the block builds from.
        what: The part of the file being built, for the message.

    Raises:
        DocumentError: In place of the :class:`DomainError`, naming ``file`` and ``what``.
    """
    try:
        yield
    except DomainError as error:
        raise DocumentError(f"{file}: {what}: {error}") from error
