"""Interfaz de línea de comandos del proyecto.

Subcomandos disponibles:

- ``mm1``: ejecuta la campaña de réplicas del servidor CI/CD M/M/1, valida los
  resultados contra las fórmulas analíticas y exporta CSV/JSON.

Los resultados se escriben por defecto en ``results/``.
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
    mm1.add_argument("--replications", type=int, default=DEFAULT_REPLICATIONS)
    mm1.add_argument("--warmup", type=float, default=DEFAULT_WARMUP)
    mm1.add_argument("--horizon", type=float, default=DEFAULT_HORIZON)
    mm1.add_argument("--seed", type=int, default=DEFAULT_BASE_SEED)
    mm1.add_argument(
        "--arrival-rate",
        type=float,
        default=0.25,
        help="Tasa de llegadas por minuto (por defecto 0,25).",
    )
    mm1.add_argument(
        "--service-rate",
        type=float,
        default=DEFAULT_SERVICE_RATE,
        help="Tasa de servicio por minuto (por defecto 1/3).",
    )
    mm1.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Carpeta donde se escriben los CSV y JSON.",
    )
    mm1.add_argument(
        "--pilot-replications",
        type=int,
        default=10,
        help="Réplicas del piloto de warm-up (0 desactiva el piloto).",
    )
    mm1.add_argument(
        "--skip-pilot",
        action="store_true",
        help="No ejecuta el piloto de warm-up.",
    )
    mm1.set_defaults(handler=_run_mm1)

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
