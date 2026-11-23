"""Interfaz de línea de comandos del proyecto.

Subcomandos disponibles:

- ``mm1``: ejecuta la campaña de réplicas del servidor CI/CD M/M/1, valida los
  resultados contra las fórmulas analíticas y exporta CSV/JSON.
- ``soc``: ejecuta el modelo base del Centro de Triaje de Incidentes (SOC) y
  exporta métricas por réplica y resumen con IC95 %.
- ``scenarios``: ejecuta la suite completa del SOC (Caso Base, Escenario A,
  Escenario B y sensibilidad bajo sobrecarga) con semillas comunes (CRN).
- ``figures``: genera las figuras PDF/PNG en ``figures/`` desde ``results/``.
- ``all``: ejecuta ``mm1``, ``scenarios`` y ``figures`` en secuencia.

Los resultados se escriben por defecto en ``results/`` y las figuras en ``figures/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Sequence

from .mm1 import (
    DEFAULT_BASE_SEED,
    DEFAULT_HORIZON,
    DEFAULT_REPLICATIONS,
    DEFAULT_SERVICE_RATE,
    DEFAULT_WARMUP,
    MM1Parameters,
    MM1Summary,
    recommend_warmup,
    run_replications,
    run_warmup_pilot,
    summarize_replications,
)
from .soc import (
    DEFAULT_ANALYSTS,
    DEFAULT_ARRIVAL_RATE_1,
    DEFAULT_ARRIVAL_RATE_2,
    DEFAULT_QUEUE_CAPACITY,
    DEFAULT_SOC_BASE_SEED,
    DEFAULT_SOC_REPLICATIONS,
    MINUTES_PER_DAY,
    SOC_METRIC_KEYS,
    SOCParameters,
    SOCScenarioSuite,
    SOCSummary,
    run_soc_replications,
    run_soc_scenarios,
    summarize_soc_replications,
)


def _add_mm1_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--replications",
        "--reps",
        dest="replications",
        type=int,
        default=DEFAULT_REPLICATIONS,
    )
    parser.add_argument(
        "--warmup",
        "--warmup-min",
        dest="warmup",
        type=float,
        default=DEFAULT_WARMUP,
    )
    parser.add_argument(
        "--horizon",
        "--horizon-min",
        dest="horizon",
        type=float,
        default=DEFAULT_HORIZON,
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_BASE_SEED)
    parser.add_argument(
        "--arrival-rate",
        type=float,
        default=0.25,
        help="Tasa de llegadas por minuto (por defecto 0,25).",
    )
    parser.add_argument(
        "--service-rate",
        type=float,
        default=DEFAULT_SERVICE_RATE,
        help="Tasa de servicio por minuto (por defecto 1/3).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Carpeta donde se escriben los CSV y JSON.",
    )
    parser.add_argument(
        "--pilot-replications",
        type=int,
        default=10,
        help="Réplicas del piloto de warm-up (0 desactiva el piloto).",
    )
    parser.add_argument(
        "--skip-pilot",
        action="store_true",
        help="No ejecuta el piloto de warm-up.",
    )


def _add_soc_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--replications",
        "--reps",
        dest="replications",
        type=int,
        default=DEFAULT_SOC_REPLICATIONS,
        help="Número de réplicas independientes (por defecto 30).",
    )
    parser.add_argument(
        "--warmup-days",
        type=float,
        default=1.0,
        help="Warm-up en días simulados (por defecto 1).",
    )
    parser.add_argument(
        "--days",
        type=float,
        default=30.0,
        help="Días de operación medida tras el warm-up (por defecto 30).",
    )
    parser.add_argument(
        "--warmup",
        "--warmup-min",
        dest="warmup_min",
        type=float,
        default=None,
        help="Warm-up explícito en minutos (sobrescribe --warmup-days).",
    )
    parser.add_argument(
        "--horizon",
        "--horizon-min",
        dest="horizon_min",
        type=float,
        default=None,
        help="Horizonte total explícito en minutos (sobrescribe --days).",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SOC_BASE_SEED)
    parser.add_argument(
        "--no-drain",
        action="store_true",
        help="No drena alertas admitidas que sigan en el sistema al alcanzar el horizonte.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Carpeta donde se escriben los CSV y JSON.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simulacion-colas",
        description="Simulación de colas: servidor CI/CD M/M/1 y SOC.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mm1 = subparsers.add_parser(
        "mm1",
        help="Ejecuta y valida el modelo M/M/1 del servidor CI/CD.",
    )
    _add_mm1_args(mm1)
    mm1.set_defaults(handler=_run_mm1)

    soc = subparsers.add_parser(
        "soc",
        help="Ejecuta el modelo base del SOC (30 días tras 1 día de warm-up).",
    )
    _add_soc_common_args(soc)
    soc.add_argument("--analysts", type=int, default=DEFAULT_ANALYSTS)
    soc.add_argument("--queue-capacity", type=int, default=DEFAULT_QUEUE_CAPACITY)
    soc.add_argument("--arrival-rate-1", type=float, default=DEFAULT_ARRIVAL_RATE_1)
    soc.add_argument("--arrival-rate-2", type=float, default=DEFAULT_ARRIVAL_RATE_2)
    soc.set_defaults(handler=_run_soc)

    scenarios = subparsers.add_parser(
        "scenarios",
        help="Ejecuta el Caso Base, Escenario A, Escenario B y sensibilidad.",
    )
    _add_soc_common_args(scenarios)
    scenarios.add_argument(
        "--figures-dir",
        type=Path,
        default=Path("figures"),
        help="Carpeta donde se guardan las figuras PDF y PNG.",
    )
    scenarios.add_argument(
        "--skip-figures",
        action="store_true",
        help="Omite la generación de figuras al terminar los escenarios.",
    )
    scenarios.set_defaults(handler=_run_scenarios)

    figures = subparsers.add_parser(
        "figures",
        help="Genera las figuras PDF/PNG desde los archivos de results/.",
    )
    figures.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Carpeta de lectura de resultados CSV/JSON.",
    )
    figures.add_argument(
        "--figures-dir",
        type=Path,
        default=Path("figures"),
        help="Carpeta donde se guardan las figuras PDF y PNG.",
    )
    figures.set_defaults(handler=_run_figures)

    run_all = subparsers.add_parser(
        "all",
        help="Ejecuta M/M/1, escenarios del SOC y generación de figuras.",
    )
    run_all.add_argument("--seed", type=int, default=DEFAULT_BASE_SEED)
    run_all.add_argument("--results-dir", type=Path, default=Path("results"))
    run_all.add_argument("--figures-dir", type=Path, default=Path("figures"))
    run_all.add_argument("--skip-pilot", action="store_true")
    run_all.add_argument("--skip-figures", action="store_true")
    run_all.set_defaults(handler=_run_all)

    return parser


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _resolve_soc_window(args: argparse.Namespace) -> tuple[float, float]:
    warmup = (
        float(args.warmup_min)
        if getattr(args, "warmup_min", None) is not None
        else float(args.warmup_days) * MINUTES_PER_DAY
    )
    if getattr(args, "horizon_min", None) is not None:
        horizon = float(args.horizon_min)
    else:
        horizon = warmup + float(args.days) * MINUTES_PER_DAY
    return warmup, horizon


def _print_summary(summary: MM1Summary) -> None:
    design = f"{summary.replications} réplicas"
    print()
    print(
        f"M/M/1 — {design}, warm-up {summary.warmup:,.0f} min, "
        f"horizonte {summary.horizon:,.0f} min"
    )
    print(
        f"lambda = {summary.parameters.arrival_rate:.4f}/min, "
        f"mu = {summary.parameters.service_rate:.6f}/min, "
        f"rho = {summary.parameters.utilization:.4f}"
    )
    print()
    header = f"{'Métrica':<12}{'Media':>10}{'IC95 %':>24}{'Analítico':>12}{'¿Contiene?':>12}"
    print(header)
    print("-" * len(header))
    for key, metric in summary.metrics.items():
        interval = metric.confidence_interval
        interval_text = f"[{interval.lower:.4f}, {interval.upper:.4f}]"
        contains = "sí" if metric.contains_analytical else "no"
        print(
            f"{key:<12}{interval.mean:>10.4f}{interval_text:>24}"
            f"{metric.analytical:>12.4f}{contains:>12}"
        )
    print()
    print(
        f"Little: L/(lambda*W) = {summary.little_L:.5f} · "
        f"Lq/(lambda*Wq) = {summary.little_Lq:.5f}"
    )


def _print_pilot(rows: list[dict[str, object]], recommended: float) -> None:
    print()
    print("Piloto de warm-up (mismas semillas, horizonte completo):")
    header = f"{'Warm-up':>10}{'L medio':>10}{'W medio':>10}{'Delta L %':>11}{'Delta W %':>11}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{float(row['warmup']):>10,.0f}{float(row['mean_L']):>10.4f}"
            f"{float(row['mean_W']):>10.4f}"
            f"{100.0 * float(row['relative_L']):>11.2f}"
            f"{100.0 * float(row['relative_W']):>11.2f}"
        )
    print(f"Warm-up recomendado por el piloto (tolerancia 0,5 %): {recommended:,.0f} min")


def _export_soc_summary(output: Path, prefix: str, summary: SOCSummary, replications: list) -> None:
    rep_rows = [rep.as_dict() for rep in replications]
    _write_csv(
        output / f"{prefix}_replicas.csv",
        rep_rows,
        fieldnames=list(rep_rows[0]),
    )

    summary_rows: list[dict[str, object]] = []
    for key in SOC_METRIC_KEYS:
        interval = summary.metrics[key]
        summary_rows.append(
            {
                "scenario_id": summary.scenario_id,
                "metric": key,
                "mean": interval.mean,
                "stdev": interval.stdev,
                "half_width": interval.half_width,
                "lower": interval.lower,
                "upper": interval.upper,
                "relative_error": interval.relative_error,
                "n": interval.n,
            }
        )
    _write_csv(
        output / f"{prefix}_summary.csv",
        summary_rows,
        fieldnames=list(summary_rows[0]),
    )
    _write_json(output / f"{prefix}_summary.json", summary.as_dict())


def _print_soc_summary(summary: SOCSummary) -> None:
    print()
    print(
        f"SOC ({summary.label}) — {summary.replications} réplicas, "
        f"warm-up {summary.warmup:,.0f} min, ventana medida {summary.measured_window:,.0f} min"
    )
    print(
        f"s = {summary.parameters.analysts}, K = {summary.parameters.queue_capacity} "
        f"(cap. total {summary.parameters.system_capacity}), "
        f"λ1 = {summary.parameters.arrival_rate_1:.4f}/min, "
        f"λ2 = {summary.parameters.arrival_rate_2:.4f}/min, "
        f"ρ_ofrecida = {summary.parameters.offered_utilization:.4f}"
    )
    print()
    header = f"{'Métrica':<14}{'Media':>12}{'IC95 %':>26}"
    print(header)
    print("-" * len(header))
    for key in ("W1", "Wq1", "W2", "Wq2", "Lq", "Lq1", "Lq2", "utilization", "P_loss", "P_loss1", "P_loss2"):
        interval = summary.metrics[key]
        if key in ("utilization", "P_loss", "P_loss1", "P_loss2"):
            mean_text = f"{100.0 * interval.mean:10.3f} %"
            ci_text = f"[{100.0 * interval.lower:.3f} %, {100.0 * interval.upper:.3f} %]"
        else:
            mean_text = f"{interval.mean:12.4f}"
            ci_text = f"[{interval.lower:.4f}, {interval.upper:.4f}]"
        print(f"{key:<14}{mean_text:>12}{ci_text:>26}")


def _print_scenarios_suite(suite: SOCScenarioSuite) -> None:
    print()
    print("Resumen comparativo de escenarios SOC (semillas comunes):")
    header = (
        f"{'Escenario':<26}{'P_loss (%)':>12}{'Util (%)':>11}"
        f"{'Wq1 (min)':>11}{'Wq2 (min)':>11}{'Lq':>9}"
    )
    print(header)
    print("-" * len(header))
    for scenario_id, summary in suite.summaries.items():
        m = summary.metrics
        print(
            f"{scenario_id:<26}"
            f"{100.0 * m['P_loss'].mean:>12.4f}"
            f"{100.0 * m['utilization'].mean:>11.2f}"
            f"{m['Wq1'].mean:>11.3f}"
            f"{m['Wq2'].mean:>11.3f}"
            f"{m['Lq'].mean:>9.3f}"
        )
    print()
    print(suite.recommendation)


def _run_mm1(args: argparse.Namespace) -> int:
    parameters = MM1Parameters(
        arrival_rate=args.arrival_rate,
        service_rate=args.service_rate,
    )
    output = Path(args.results_dir)
    output.mkdir(parents=True, exist_ok=True)

    if not args.skip_pilot and args.pilot_replications > 0:
        candidates = tuple(
            value for value in (0.0, 500.0, 1_000.0, 2_000.0, 5_000.0) if value < args.horizon
        )
        pilot = run_warmup_pilot(
            parameters,
            candidates=candidates,
            replications=args.pilot_replications,
            base_seed=args.seed,
            horizon=args.horizon,
        )
        pilot_rows = [row.as_dict() for row in pilot]
        _write_csv(
            output / "mm1_warmup_pilot.csv",
            pilot_rows,
            fieldnames=list(pilot_rows[0]),
        )
        recommended = recommend_warmup(pilot)
        _print_pilot(pilot_rows, recommended)

    replications = run_replications(
        parameters,
        replications=args.replications,
        base_seed=args.seed,
        warmup=args.warmup,
        horizon=args.horizon,
    )
    summary = summarize_replications(replications, parameters)

    replication_rows = [replication.as_dict() for replication in replications]
    _write_csv(
        output / "mm1_replicas.csv",
        replication_rows,
        fieldnames=list(replication_rows[0]),
    )

    summary_rows: list[dict[str, object]] = []
    for key, metric in summary.metrics.items():
        row = {"metric": key}
        row.update(metric.as_dict())
        summary_rows.append(row)
    _write_csv(
        output / "mm1_summary.csv",
        summary_rows,
        fieldnames=list(summary_rows[0]),
    )
    _write_json(output / "mm1_summary.json", summary.as_dict())

    _print_summary(summary)
    print(f"Resultados escritos en: {output.resolve()}")
    return 0


def _run_soc(args: argparse.Namespace) -> int:
    parameters = SOCParameters(
        analysts=args.analysts,
        queue_capacity=args.queue_capacity,
        arrival_rate_1=args.arrival_rate_1,
        arrival_rate_2=args.arrival_rate_2,
    )
    warmup, horizon = _resolve_soc_window(args)
    drain = not bool(args.no_drain)
    output = Path(args.results_dir)
    output.mkdir(parents=True, exist_ok=True)

    replications = run_soc_replications(
        parameters,
        replications=args.replications,
        base_seed=args.seed,
        warmup=warmup,
        horizon=horizon,
        drain=drain,
    )
    summary = summarize_soc_replications(
        replications,
        parameters,
        scenario_id="base",
        label=f"SOC base (s={parameters.analysts}, K={parameters.queue_capacity})",
    )
    _export_soc_summary(output, "soc_base", summary, replications)
    _print_soc_summary(summary)
    print(f"Resultados escritos en: {output.resolve()}")
    return 0


def _run_scenarios(args: argparse.Namespace) -> int:
    warmup, horizon = _resolve_soc_window(args)
    drain = not bool(args.no_drain)
    output = Path(args.results_dir)
    output.mkdir(parents=True, exist_ok=True)

    suite = run_soc_scenarios(
        replications=args.replications,
        base_seed=args.seed,
        warmup=warmup,
        horizon=horizon,
        drain=drain,
    )

    # Exportar caso base por compatibilidad directa con el subcomando soc
    _export_soc_summary(
        output,
        "soc_base",
        suite.summaries["base"],
        suite.replications_by_scenario["base"],
    )

    # Exportar todas las réplicas apiladas
    all_rep_rows: list[dict[str, object]] = []
    for scenario_id, runs in suite.replications_by_scenario.items():
        summary = suite.summaries[scenario_id]
        for run in runs:
            row: dict[str, object] = {
                "scenario_id": scenario_id,
                "analysts": summary.parameters.analysts,
                "queue_capacity": summary.parameters.queue_capacity,
                "arrival_rate_1": summary.parameters.arrival_rate_1,
                "arrival_rate_2": summary.parameters.arrival_rate_2,
            }
            row.update(run.as_dict())
            all_rep_rows.append(row)
    _write_csv(
        output / "soc_scenarios_replicas.csv",
        all_rep_rows,
        fieldnames=list(all_rep_rows[0]),
    )

    # Exportar tabla resumen de escenarios
    summary_rows: list[dict[str, object]] = []
    for scenario_id, summary in suite.summaries.items():
        for metric_key in SOC_METRIC_KEYS:
            interval = summary.metrics[metric_key]
            summary_rows.append(
                {
                    "scenario_id": scenario_id,
                    "label": summary.label,
                    "analysts": summary.parameters.analysts,
                    "queue_capacity": summary.parameters.queue_capacity,
                    "arrival_rate_1": summary.parameters.arrival_rate_1,
                    "arrival_rate_2": summary.parameters.arrival_rate_2,
                    "offered_utilization": summary.parameters.offered_utilization,
                    "metric": metric_key,
                    "mean": interval.mean,
                    "stdev": interval.stdev,
                    "half_width": interval.half_width,
                    "lower": interval.lower,
                    "upper": interval.upper,
                    "relative_error": interval.relative_error,
                    "n": interval.n,
                }
            )
    _write_csv(
        output / "soc_scenarios_summary.csv",
        summary_rows,
        fieldnames=list(summary_rows[0]),
    )

    # Exportar comparaciones pareadas
    comparison_rows = [row.as_dict() for row in suite.comparisons]
    _write_csv(
        output / "soc_scenarios_comparisons.csv",
        comparison_rows,
        fieldnames=list(comparison_rows[0]),
    )

    # Exportar JSON completo
    _write_json(output / "soc_scenarios_summary.json", suite.as_dict())

    _print_scenarios_suite(suite)
    print(f"Resultados escritos en: {output.resolve()}")

    if not getattr(args, "skip_figures", False):
        from .figures import generate_all_figures

        generated = generate_all_figures(output, Path(args.figures_dir))
        print(f"Figuras generadas ({len(generated)} archivos) en: {Path(args.figures_dir).resolve()}")
    return 0


def _run_figures(args: argparse.Namespace) -> int:
    from .figures import generate_all_figures

    generated = generate_all_figures(Path(args.results_dir), Path(args.figures_dir))
    for path in generated:
        print(f"Figura generada: {path}")
    return 0


def _run_all(args: argparse.Namespace) -> int:
    mm1_args = argparse.Namespace(
        replications=DEFAULT_REPLICATIONS,
        warmup=DEFAULT_WARMUP,
        horizon=DEFAULT_HORIZON,
        seed=args.seed,
        arrival_rate=0.25,
        service_rate=DEFAULT_SERVICE_RATE,
        results_dir=args.results_dir,
        pilot_replications=10,
        skip_pilot=args.skip_pilot,
    )
    _run_mm1(mm1_args)

    scenarios_args = argparse.Namespace(
        replications=DEFAULT_SOC_REPLICATIONS,
        warmup_days=1.0,
        days=30.0,
        warmup_min=None,
        horizon_min=None,
        seed=args.seed,
        no_drain=False,
        results_dir=args.results_dir,
        figures_dir=args.figures_dir,
        skip_figures=args.skip_figures,
    )
    _run_scenarios(scenarios_args)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error("Subcomando no reconocido.")
    return int(handler(args))


def _configure_console() -> None:
    """Usa UTF-8 en consolas modernas y evita fallos con acentos y símbolos."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
