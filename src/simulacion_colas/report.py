"""Generación de tablas LaTeX a partir de los resultados versionados.

El informe nunca debe editar números a mano. Este módulo lee los CSV/JSON de
``results/`` y escribe tablas ``.tex`` en ``docs/informe/tables/`` para que el
documento las incorpore con ``\\input``. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

TABLE_NAMES = (
    "tab_mm1_parametros.tex",
    "tab_mm1_validacion.tex",
    "tab_warmup.tex",
    "tab_soc_parametros.tex",
    "tab_soc_base.tex",
    "tab_conteos.tex",
    "tab_conservacion.tex",
    "tab_escenario_a.tex",
    "tab_escenario_b_demanda.tex",
    "tab_escenario_b_sobrecarga.tex",
)

_HEADER = (
    "% Tabla generada automáticamente por simulacion_colas.report.\n"
    "% No editar a mano: regenerar con `python -m simulacion_colas report`.\n"
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: float, decimals: int = 4) -> str:
    """Formatea un número con coma decimal para el documento en español."""
    return f"{value:.{decimals}f}".replace(".", ",")


def _signed(value: float, decimals: int = 4) -> str:
    text = _num(value, decimals)
    return f"+{text}" if value > 0 else text


def _pct(value: float, decimals: int = 3) -> str:
    return f"{_num(100.0 * value, decimals)}\\,\\%"


def _pp(value: float, decimals: int = 3) -> str:
    text = _signed(100.0 * value, decimals)
    return f"{text}\\,pp"


def _ci(lower: float, upper: float, decimals: int = 4, scale: float = 1.0) -> str:
    return (
        f"[{_num(scale * lower, decimals)}; "
        f"{_num(scale * upper, decimals)}]"
    )


def _write(path: Path, lines: Iterable[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_mm1_parameters(payload: dict[str, Any]) -> list[str]:
    parameters = payload["parameters"]
    analytical = payload["analytical"]
    rows = (
        ("Tasa de llegadas $\\lambda$", parameters["arrival_rate"], "trabajos/min"),
        ("Tasa de servicio $\\mu$", parameters["service_rate"], "trabajos/min"),
        ("Utilización $\\rho=\\lambda/\\mu$", analytical["rho"], "--"),
        ("Número medio en el sistema $L$", analytical["L"], "trabajos"),
        ("Número medio en cola $L_q$", analytical["Lq"], "trabajos"),
        ("Tiempo medio en el sistema $W$", analytical["W"], "min"),
        ("Tiempo medio en cola $W_q$", analytical["Wq"], "min"),
    )
    lines = [
        "\\begin{tabular}{lrl}",
        "\\toprule",
        "Parámetro & Valor & Unidad \\\\",
        "\\midrule",
    ]
    for label, value, unit in rows:
        lines.append(f"{label} & {_num(float(value), 4)} & {unit} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_mm1_validation(rows: list[dict[str, str]]) -> list[str]:
    metrics = (
        ("$L$", "L", "trabajos"),
        ("$L_q$", "Lq", "trabajos"),
        ("$W$", "W", "min"),
        ("$W_q$", "Wq", "min"),
        ("$\\rho$", "utilization", "--"),
    )
    indexed = {row["metric"]: row for row in rows}
    lines = [
        "\\begin{tabular}{llrrrl}",
        "\\toprule",
        "Métrica & Unidad & Media & IC95\\,\\% & Analítico & ¿Contiene? \\\\",
        "\\midrule",
    ]
    for label, key, unit in metrics:
        row = indexed[key]
        contains = "Sí" if row["contains_analytical"] == "True" else "No"
        lines.append(
            f"{label} & {unit} & {_num(float(row['mean']))} & "
            f"{_ci(float(row['lower']), float(row['upper']))} & "
            f"{_num(float(row['analytical']))} & {contains} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_warmup(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "\\begin{tabular}{rrrrr}",
        "\\toprule",
        "Warm-up (min) & $L$ & $W$ (min) & $\\Delta L$ (\\%) & $\\Delta W$ (\\%) \\\\",
        "\\midrule",
    ]
    for row in rows:
        warmup = float(row["warmup"])
        label = f"{warmup:,.0f}".replace(",", ".")
        if warmup == 1000.0:
            label = f"\\textbf{{{label}}}"
        lines.append(
            f"{label} & {_num(float(row['mean_L']))} & "
            f"{_num(float(row['mean_W']))} & "
            f"{_num(100.0 * float(row['relative_L']), 3)} & "
            f"{_num(100.0 * float(row['relative_W']), 3)} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_soc_parameters(payload: dict[str, Any]) -> list[str]:
    scenarios = payload["scenarios"]
    order = (
        ("base", "Base"),
        ("scenario_a", "A (+40\\,\\%)"),
        ("scenario_b_k16", "B1: $K=16$"),
        ("scenario_b_s4", "B2: $s=4$"),
        ("scenario_b_k16_overload", "B1 con sobrecarga A"),
        ("scenario_b_s4_overload", "B2 con sobrecarga A"),
    )
    lines = [
        "\\begin{tabular}{lrrrrr}",
        "\\toprule",
        "Escenario & $s$ & $K$ & $\\lambda_2$ (/min) & "
        "$\\rho_{\\text{ofrecida}}$ & Capacidad total \\\\",
        "\\midrule",
    ]
    for scenario_id, label in order:
        parameters = scenarios[scenario_id]["parameters"]
        lines.append(
            f"{label} & {int(parameters['analysts'])} & "
            f"{int(parameters['queue_capacity'])} & "
            f"{_num(float(parameters['arrival_rate_2']), 2)} & "
            f"{_num(float(parameters['offered_utilization']))} & "
            f"{int(parameters['system_capacity'])} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_soc_base(rows: list[dict[str, str]]) -> list[str]:
    metrics = (
        ("$W_1$", "W1", "min", 1.0, 4),
        ("$W_{q1}$", "Wq1", "min", 1.0, 4),
        ("$W_2$", "W2", "min", 1.0, 4),
        ("$W_{q2}$", "Wq2", "min", 1.0, 4),
        ("$W$", "W", "min", 1.0, 4),
        ("$W_q$", "Wq", "min", 1.0, 4),
        ("$L$", "L", "trabajos", 1.0, 4),
        ("$L_q$", "Lq", "trabajos", 1.0, 4),
        ("$L_{q1}$", "Lq1", "trabajos", 1.0, 4),
        ("$L_{q2}$", "Lq2", "trabajos", 1.0, 4),
        ("Utilización", "utilization", "\\%", 100.0, 2),
        ("$P_{\\text{loss}}$", "P_loss", "\\%", 100.0, 4),
        ("$P_{\\text{loss},1}$", "P_loss1", "\\%", 100.0, 4),
        ("$P_{\\text{loss},2}$", "P_loss2", "\\%", 100.0, 4),
    )
    indexed = {row["metric"]: row for row in rows}
    lines = [
        "\\begin{tabular}{llrrr}",
        "\\toprule",
        "Métrica & Unidad & Media & IC95\\,\\% & Error rel. (\\%) \\\\",
        "\\midrule",
    ]
    for label, key, unit, scale, decimals in metrics:
        row = indexed[key]
        lines.append(
            f"{label} & {unit} & {_num(scale * float(row['mean']), decimals)} & "
            f"{_ci(float(row['lower']), float(row['upper']), decimals, scale)} & "
            f"{_num(100.0 * float(row['relative_error']), 2)} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_counts(rows: list[dict[str, str]]) -> list[str]:
    def mean(key: str) -> float:
        return sum(float(row[key]) for row in rows) / len(rows)

    concepts = (
        ("Llegadas", "arrivals", "arrivals_1", "arrivals_2"),
        ("Admitidas", "admitted", "admitted_1", "admitted_2"),
        ("Bloqueadas", "blocked", "blocked_1", "blocked_2"),
        ("Completadas", "completed", "completed_1", "completed_2"),
        ("Remanentes al final", "remaining", "remaining_1", "remaining_2"),
    )
    lines = [
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Concepto & Total & Tipo 1 (críticas) & Tipo 2 (preventivas) \\\\",
        "\\midrule",
    ]
    for label, total, first, second in concepts:
        lines.append(
            f"{label} & {_num(mean(total), 1)} & "
            f"{_num(mean(first), 1)} & {_num(mean(second), 1)} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_conservation(rows: list[dict[str, str]]) -> list[str]:
    checks = (
        (
            "Llegadas $=$ admitidas $+$ bloqueadas",
            lambda row: int(row["arrivals"]) == int(row["admitted"]) + int(row["blocked"]),
        ),
        (
            "Admitidas $=$ completadas $+$ remanentes",
            lambda row: int(row["admitted"]) == int(row["completed"]) + int(row["remaining"]),
        ),
        (
            "Bloqueadas $=$ bloqueadas T1 $+$ T2",
            lambda row: int(row["blocked"]) == int(row["blocked_1"]) + int(row["blocked_2"]),
        ),
        (
            "Admitidas $=$ admitidas T1 $+$ T2",
            lambda row: int(row["admitted"]) == int(row["admitted_1"]) + int(row["admitted_2"]),
        ),
        (
            "Analistas ocupados $\\le 3$ y cola $\\le 8$",
            lambda row: int(row["max_busy_analysts"]) <= 3 and int(row["max_queue_length"]) <= 8,
        ),
    )
    lines = [
        "\\begin{tabular}{lrr}",
        "\\toprule",
        "Verificación por réplica & Réplicas que cumplen & Total \\\\",
        "\\midrule",
    ]
    for label, check in checks:
        passed = sum(1 for row in rows if check(row))
        lines.append(f"{label} & {passed} & {len(rows)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def build_scenario_a(
    comparisons: list[dict[str, str]],
    base_rows: list[dict[str, str]],
) -> list[str]:
    comparison = {
        row["metric"]: row
        for row in comparisons
        if row["comparison_id"] == "scenario_a_vs_base"
    }
    base = {row["metric"]: row for row in base_rows}
    metrics = (
        ("$W_1$", "W1", "min", 1.0, 4),
        ("$W_{q1}$", "Wq1", "min", 1.0, 4),
        ("$W_2$", "W2", "min", 1.0, 4),
        ("$W_{q2}$", "Wq2", "min", 1.0, 4),
        ("$L_q$", "Lq", "trabajos", 1.0, 4),
        ("Utilización", "utilization", "\\%", 100.0, 2),
        ("$P_{\\text{loss}}$", "P_loss", "\\%", 100.0, 4),
        ("$P_{\\text{loss},1}$", "P_loss1", "\\%", 100.0, 4),
        ("$P_{\\text{loss},2}$", "P_loss2", "\\%", 100.0, 4),
    )
    lines = [
        "\\begin{tabular}{llrrrrr}",
        "\\toprule",
        "Métrica & Unidad & Base & Escenario A & Diferencia & "
        "IC95\\,\\% de la diferencia & Cambio rel. (\\%) \\\\",
        "\\midrule",
    ]
    for label, key, unit, scale, decimals in metrics:
        reference = float(comparison[key]["reference_mean"])
        alternative = float(comparison[key]["alternative_mean"])
        difference = float(comparison[key]["diff_mean"])
        lower = float(comparison[key]["diff_lower"])
        upper = float(comparison[key]["diff_upper"])
        relative = 100.0 * float(comparison[key]["relative_change"])
        if key in ("utilization", "P_loss", "P_loss1", "P_loss2"):
            difference_text = _pp(difference)
            interval_text = f"[{_num(100.0 * lower, 3)}; {_num(100.0 * upper, 3)}]"
        else:
            difference_text = _signed(difference, decimals)
            interval_text = _ci(lower, upper, decimals)
        lines.append(
            f"{label} & {unit} & {_num(scale * reference, decimals)} & "
            f"{_num(scale * alternative, decimals)} & {difference_text} & "
            f"{interval_text} & {_signed(relative, 1)} \\\\"
        )
    # Aunque la tabla no usa ``base`` para los valores, se conserva la
    # comprobación de que las réplicas base están disponibles.
    assert base["P_loss"]["mean"]
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def _scenario_cell(
    payload: dict[str, Any],
    scenario_id: str,
    metric: str,
    decimals: int,
    scale: float,
) -> str:
    entry = payload["scenarios"][scenario_id]["metrics"][metric]
    mean = scale * float(entry["mean"])
    half_width = scale * float(entry["half_width"])
    return f"{_num(mean, decimals)} $\\pm$ {_num(half_width, decimals)}"


def build_scenario_b(
    payload: dict[str, Any],
    *,
    overload: bool,
) -> list[str]:
    if overload:
        columns = (
            ("scenario_a", "Base A"),
            ("scenario_b_k16_overload", "$K=16$"),
            ("scenario_b_s4_overload", "$s=4$"),
        )
    else:
        columns = (
            ("base", "Base"),
            ("scenario_b_k16", "$K=16$"),
            ("scenario_b_s4", "$s=4$"),
        )
    metrics = (
        ("$P_{\\text{loss}}$ (\\%)", "P_loss", 3, 100.0),
        ("Utilización (\\%)", "utilization", 2, 100.0),
        ("$W_{q1}$ (min)", "Wq1", 3, 1.0),
        ("$W_{q2}$ (min)", "Wq2", 3, 1.0),
        ("$W_1$ (min)", "W1", 3, 1.0),
        ("$W_2$ (min)", "W2", 3, 1.0),
        ("$L_q$ (trabajos)", "Lq", 3, 1.0),
    )
    lines = [
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        f"Métrica & {columns[0][1]} & {columns[1][1]} & {columns[2][1]} \\\\",
        "\\midrule",
    ]
    for label, metric, decimals, scale in metrics:
        cells = [
            _scenario_cell(payload, scenario_id, metric, decimals, scale)
            for scenario_id, _ in columns
        ]
        lines.append(f"{label} & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return lines


def generate_report_tables(
    results_dir: Path = Path("results"),
    tables_dir: Path = Path("docs/informe/tables"),
) -> list[Path]:
    """Genera todas las tablas LaTeX y devuelve las rutas escritas."""
    mm1_payload = _read_json(results_dir / "mm1_summary.json")
    mm1_rows = _read_csv(results_dir / "mm1_summary.csv")
    warmup_rows = _read_csv(results_dir / "mm1_warmup_pilot.csv")
    soc_payload = _read_json(results_dir / "soc_scenarios_summary.json")
    soc_base_rows = _read_csv(results_dir / "soc_base_summary.csv")
    comparisons = _read_csv(results_dir / "soc_scenarios_comparisons.csv")
    replication_rows = _read_csv(results_dir / "soc_base_replicas.csv")

    builders = {
        "tab_mm1_parametros.tex": build_mm1_parameters(mm1_payload),
        "tab_mm1_validacion.tex": build_mm1_validation(mm1_rows),
        "tab_warmup.tex": build_warmup(warmup_rows),
        "tab_soc_parametros.tex": build_soc_parameters(soc_payload),
        "tab_soc_base.tex": build_soc_base(soc_base_rows),
        "tab_conteos.tex": build_counts(replication_rows),
        "tab_conservacion.tex": build_conservation(replication_rows),
        "tab_escenario_a.tex": build_scenario_a(comparisons, soc_base_rows),
        "tab_escenario_b_demanda.tex": build_scenario_b(soc_payload, overload=False),
        "tab_escenario_b_sobrecarga.tex": build_scenario_b(soc_payload, overload=True),
    }
    generated: list[Path] = []
    for name in TABLE_NAMES:
        generated.append(_write(tables_dir / name, builders[name]))
    return generated
