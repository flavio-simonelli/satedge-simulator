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


def test_the_help_is_in_italian(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["run", "--help"])
    assert raised.value.code == 0
    help_text = capsys.readouterr().out
    assert help_text.startswith(
        "uso: satedge-simulator run [-h] [-o CARTELLA] scenario"
    )
    assert "mostra questo aiuto ed esce" in help_text
    assert "argomenti:" in help_text
    assert "opzioni:" in help_text


def test_argument_errors_are_in_italian(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["run"])
    assert capsys.readouterr().err.endswith(
        "errore: mancano gli argomenti obbligatori: scenario\n"
    )


STOCHASTIC = SCENARIO.parent / "scenario-stocastico.yaml"


def test_replicate_reports_the_estimates_in_italian(tmp_path: Path) -> None:
    out = io.StringIO()
    code = main(
        [
            "replicate",
            str(STOCHASTIC),
            "-n",
            "2",
            "--cell",
            "7200",
            "--welch",
            "1",
            "-o",
            str(tmp_path),
        ],
        out=out,
    )
    assert code == 0
    lines = out.getvalue().splitlines()
    assert lines[0].startswith("Orizzonte finito: 2 repliche dal seed 123456789")
    assert any(
        line.startswith("  utilizzo degli HPC: ") and "(2 repliche)" in line
        for line in lines
    )
    assert (tmp_path / "replications.json").is_file()
    assert (
        (tmp_path / "transient.csv")
        .read_text(encoding="utf-8")
        .startswith("statistic,start_s")
    )


def test_batch_needs_the_warmup(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["batch", str(STOCHASTIC)])
    assert "mancano gli argomenti obbligatori: --warmup" in capsys.readouterr().err


def test_batch_reports_the_batch_means(tmp_path: Path) -> None:
    out = io.StringIO()
    code = main(
        ["batch", str(STOCHASTIC), "--warmup", "5640", "-b", "4", "-o", str(tmp_path)],
        out=out,
    )
    assert code == 0
    assert "(4 batch)" in out.getvalue()
    assert (tmp_path / "batches.csv").is_file()


def test_autocorrelation_reports_the_lag_where_it_fades(tmp_path: Path) -> None:
    out = io.StringIO()
    code = main(
        [
            "autocorrelation",
            str(STOCHASTIC),
            "--warmup",
            "0",
            "--max-lag",
            "3",
            "-o",
            str(tmp_path),
        ],
        out=out,
    )
    assert code == 0
    assert "tempo di risposta dal rilascio (s):" in out.getvalue()
    assert (
        (tmp_path / "autocorrelation.csv")
        .read_text(encoding="utf-8")
        .startswith("statistic,lag,r")
    )
