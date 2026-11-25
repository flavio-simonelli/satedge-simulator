"""Tests of the command line."""

import io
from pathlib import Path

import pytest

from satedge_simulator.cli import main

SCENARIO = Path(__file__).parent.parent / "examples" / "casostudio" / "scenario.yaml"


def test_run_reports_the_simulation_in_italian(tmp_path: Path) -> None:
    out = io.StringIO()
    assert main(["run", str(SCENARIO), "-o", str(tmp_path)], out=out) == 0
    lines = out.getvalue().splitlines()
    assert lines[0] == "Simulazione conclusa a 28800 s."
    assert lines[1].startswith("Richieste urgenti: 4 arrivate, 4 accettate")
    assert "Violazioni del piano: nessuna." in lines
    assert "Verifica dell'esecuzione con il modello: superata." in lines
    assert lines[-1] == f"Risultati in {tmp_path}."
    assert (tmp_path / "metrics.json").is_file()


def test_a_scenario_that_cannot_be_read_exits_with_1(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "missing.yaml"]) == 1
    assert capsys.readouterr().err.startswith("errore: missing.yaml")


def test_wrong_arguments_exit_with_2() -> None:
    with pytest.raises(SystemExit) as raised:
        main([])
    assert raised.value.code == 2
