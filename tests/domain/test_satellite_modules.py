"""Tests of the satellite and of its three modules."""

from collections.abc import Callable

import pytest

from satedge_simulator.domain.intervals import Window, WindowSet
from satedge_simulator.domain.satellite import (
    HpcModule,
    LinkKind,
    OctModule,
    PlmmModule,
    Satellite,
    Terminal,
)
from satedge_simulator.errors import DomainError


def satellite(**changes: object) -> Satellite:
    fields: dict[str, object] = {
        "id": "S1",
        "plmm": PlmmModule(100.0),
        "hpc": HpcModule(1.0, WindowSet([Window(0.0, 10.0)])),
        "oct": OctModule((Terminal(LinkKind.GROUND, 1.0),)),
        **changes,
    }
    return Satellite(**fields)  # type: ignore[arg-type]


def test_the_modules_are_kept_as_given() -> None:
    s = satellite()
    assert s.plmm.capacity_gb == 100.0
    assert s.hpc.rate_gbps == 1.0
    assert s.oct.terminals[0].kind is LinkKind.GROUND


def test_the_hpc_io_time_is_size_over_rate() -> None:
    assert HpcModule(2.0, WindowSet()).io_time(8.0) == 4.0


@pytest.mark.parametrize(
    "make",
    [
        lambda: satellite(id=""),
        lambda: satellite(plmm=PlmmModule(0.0)),
        lambda: satellite(hpc=HpcModule(0.0, WindowSet())),
        lambda: satellite(oct=OctModule(())),
        lambda: satellite(oct=OctModule((Terminal(LinkKind.INTER_ORBIT, -1.0),))),
    ],
)
def test_invalid_satellites_are_rejected(make: Callable[[], Satellite]) -> None:
    with pytest.raises(DomainError):
        make()
