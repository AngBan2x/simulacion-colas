"""Pruebas de la generación de tablas LaTeX del informe."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from simulacion_colas.cli import main
from simulacion_colas.report import TABLE_NAMES, generate_report_tables


def test_report_tables_are_generated_from_versioned_results(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    generated = generate_report_tables(repo_root / "results", tmp_path)

    assert {path.name for path in generated} == set(TABLE_NAMES)
    for path in generated:
        assert path.is_file()
        assert path.stat().st_size > 0

    validation = (tmp_path / "tab_mm1_validacion.tex").read_text(encoding="utf-8")
    assert "3,0466" in validation
    assert "2,9712" in validation
    assert "Sí" in validation

    scenario_a = (tmp_path / "tab_escenario_a.tex").read_text(encoding="utf-8")
    assert "2,2201" in scenario_a
    assert "+1,835" in scenario_a
    assert "+477,0" in scenario_a

    scenario_b = (tmp_path / "tab_escenario_b_sobrecarga.tex").read_text(encoding="utf-8")
    assert "0,129" in scenario_b
    assert "0,395" in scenario_b
    assert "17,414" in scenario_b

    base = (tmp_path / "tab_soc_base.tex").read_text(encoding="utf-8")
    assert "0,3847" in base
    assert "68,87" in base

    conservation = (tmp_path / "tab_conservacion.tex").read_text(encoding="utf-8")
    assert conservation.count("& 30 & 30") == 5


def test_report_cli_writes_tables(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert main(
        [
            "report",
            "--results-dir",
            str(repo_root / "results"),
            "--tables-dir",
            str(tmp_path),
        ]
    ) == 0
    for name in TABLE_NAMES:
        assert (tmp_path / name).is_file()


def test_latex_inputs_and_figures_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    informer = repo_root / "docs" / "informe"
    main_tex = (informer / "main.tex").read_text(encoding="utf-8")

    inputs = re.findall(r"\\input\{([^}]+)\}", main_tex)
    assert inputs, "main.tex debe incluir secciones con \\input"
    for relative in inputs:
        path = informer / relative
        if not path.suffix:
            path = path.with_suffix(".tex")
        assert path.is_file(), f"Falta {path}"

    sections = list((informer / "sections").glob("*.tex"))
    assert sections
    for section in sections:
        content = section.read_text(encoding="utf-8")
        for relative in re.findall(r"\\input\{([^}]+)\}", content):
            path = informer / relative
            if not path.suffix:
                path = path.with_suffix(".tex")
            assert path.is_file(), f"Falta {path}"

        for graphic in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", content):
            assert (repo_root / "figures" / graphic).is_file(), f"Falta figures/{graphic}"


def test_generated_tables_are_committed_in_sync_with_results() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    committed = repo_root / "docs" / "informe" / "tables"
    assert committed.is_dir()
    for name in TABLE_NAMES:
        assert (committed / name).is_file(), f"Falta la tabla versionada {name}"


def test_versioned_soc_results_satisfy_conservation() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    with (repo_root / "results" / "soc_base_replicas.csv").open(
        encoding="utf-8", newline=""
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 30
    for row in rows:
        assert int(row["arrivals"]) == int(row["admitted"]) + int(row["blocked"])
        assert int(row["admitted"]) == int(row["completed"]) + int(row["remaining"])
        assert int(row["blocked"]) == int(row["blocked_1"]) + int(row["blocked_2"])
        assert int(row["admitted"]) == int(row["admitted_1"]) + int(row["admitted_2"])
        assert int(row["max_busy_analysts"]) <= 3
        assert int(row["max_queue_length"]) <= 8
