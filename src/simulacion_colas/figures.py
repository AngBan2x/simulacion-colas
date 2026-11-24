"""Generación de figuras reproducibles a partir de los resultados en ``results/``.

Este módulo aísla ``matplotlib`` del núcleo de simulación (que depende solo de
la biblioteca estándar). Todas las gráficas se generan directamente desde los
archivos JSON/CSV versionados y se guardan en ``figures/`` en formatos PDF
(vectorial para LaTeX) y PNG (300 dpi).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _load_matplotlib():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
        }
    )
    return plt


def _save_figure(fig: Any, figures_dir: Path, stem: str) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    outputs: list[Path] = []
    for ext in ("pdf", "png"):
        target = figures_dir / f"{stem}.{ext}"
        save_kwargs: dict[str, Any] = {"bbox_inches": "tight"}
        if ext == "png":
            save_kwargs["dpi"] = 300
        fig.savefig(target, **save_kwargs)
        outputs.append(target)
    return outputs


def generate_mm1_validation_figure(
    results_dir: Path,
    figures_dir: Path,
) -> list[Path]:
    """Genera ``mm1_validation.{pdf,png}`` desde ``mm1_summary.json`` y el piloto."""
    summary_path = results_dir / "mm1_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"No se encontró {summary_path}.")

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]

    pilot_path = results_dir / "mm1_warmup_pilot.csv"
    pilot_rows: list[dict[str, str]] = []
    if pilot_path.is_file():
        with pilot_path.open(encoding="utf-8", newline="") as file:
            pilot_rows = list(csv.DictReader(file))

    plt = _load_matplotlib()
    ncols = 3 if pilot_rows else 2
    fig, axes = plt.subplots(1, ncols, figsize=(4.8 * ncols, 4.1))

    # Panel A: L, Lq y rho
    ax0 = axes[0]
    keys_left = ["L", "Lq", "utilization"]
    labels_left = ["L", "Lq", "ρ (util.)"]
    sim_means = [metrics[k]["mean"] for k in keys_left]
    sim_hw = [metrics[k]["half_width"] for k in keys_left]
    ana_vals = [metrics[k]["analytical"] for k in keys_left]
    x_pos = list(range(len(keys_left)))

    ax0.bar(
        x_pos,
        sim_means,
        yerr=sim_hw,
        capsize=4,
        width=0.52,
        color="#2b6cb0",
        alpha=0.85,
        label="Simulación (IC95 %)",
    )
    ax0.scatter(
        x_pos,
        ana_vals,
        marker="D",
        s=55,
        color="#c53030",
        zorder=5,
        label="Valor analítico",
    )
    ax0.set_xticks(x_pos, labels_left)
    ax0.set_ylabel("Trabajos / proporción")
    ax0.set_title("Cantidades y utilización M/M/1")
    ax0.legend(loc="upper right", frameon=True)

    # Panel B: W y Wq en minutos
    ax1 = axes[1]
    keys_mid = ["W", "Wq"]
    labels_mid = ["W (sistema)", "Wq (cola)"]
    sim_means_t = [metrics[k]["mean"] for k in keys_mid]
    sim_hw_t = [metrics[k]["half_width"] for k in keys_mid]
    ana_vals_t = [metrics[k]["analytical"] for k in keys_mid]
    x_pos_t = list(range(len(keys_mid)))

    ax1.bar(
        x_pos_t,
        sim_means_t,
        yerr=sim_hw_t,
        capsize=4,
        width=0.48,
        color="#2f855a",
        alpha=0.85,
        label="Simulación (IC95 %)",
    )
    ax1.scatter(
        x_pos_t,
        ana_vals_t,
        marker="D",
        s=55,
        color="#c53030",
        zorder=5,
        label="Valor analítico",
    )
    ax1.set_xticks(x_pos_t, labels_mid)
    ax1.set_ylabel("Minutos")
    ax1.set_title("Tiempos medios M/M/1")
    ax1.legend(loc="upper right", frameon=True)

    # Panel C: Piloto de warm-up si está disponible
    if pilot_rows:
        ax2 = axes[2]
        warmups = [float(row["warmup"]) for row in pilot_rows]
        rel_l = [100.0 * float(row["relative_L"]) for row in pilot_rows]
        rel_w = [100.0 * float(row["relative_W"]) for row in pilot_rows]

        ax2.plot(warmups, rel_l, marker="o", linewidth=1.8, color="#2b6cb0", label="Δ L (%)")
        ax2.plot(warmups, rel_w, marker="s", linewidth=1.8, color="#d69e2e", label="Δ W (%)")
        ax2.axhspan(-0.5, 0.5, color="#c6f6d5", alpha=0.55, label="Banda ±0,5 %")
        ax2.axhline(0.0, color="#4a5568", linewidth=0.9)
        ax2.axvline(float(payload["design"]["warmup"]), color="#c53030", linestyle=":", linewidth=1.3, label="Warm-up elegido")
        ax2.set_xlabel("Warm-up (min)")
        ax2.set_ylabel("Diferencia respecto a 5.000 min (%)")
        ax2.set_title("Piloto de período transitorio")
        ax2.legend(loc="best", frameon=True, fontsize=7.8)

    fig.suptitle(
        f"Validación del servidor CI/CD M/M/1 ({payload['design']['replications']} réplicas, "
        f"IC95 %)",
        fontsize=11.5,
        fontweight="bold",
    )
    outputs = _save_figure(fig, figures_dir, "mm1_validation")
    plt.close(fig)
    return outputs


def generate_soc_scenario_a_figure(
    results_dir: Path,
    figures_dir: Path,
) -> list[Path]:
    """Genera ``soc_scenario_a.{pdf,png}`` comparando Caso Base vs. Escenario A."""
    summary_path = results_dir / "soc_scenarios_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"No se encontró {summary_path}.")

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    base = payload["scenarios"]["base"]
    scen_a = payload["scenarios"]["scenario_a"]

    plt = _load_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.4))

    # Panel A: Probabilidad de bloqueo (%)
    ax0 = axes[0]
    loss_keys = ["P_loss", "P_loss1", "P_loss2"]
    loss_labels = ["Global", "Críticas (T1)", "Preventivas (T2)"]
    x = [0, 1, 2]
    width = 0.35

    base_loss = [100.0 * base["metrics"][k]["mean"] for k in loss_keys]
    base_loss_hw = [100.0 * base["metrics"][k]["half_width"] for k in loss_keys]
    a_loss = [100.0 * scen_a["metrics"][k]["mean"] for k in loss_keys]
    a_loss_hw = [100.0 * scen_a["metrics"][k]["half_width"] for k in loss_keys]

    ax0.bar(
        [i - width / 2 for i in x],
        base_loss,
        yerr=base_loss_hw,
        capsize=3.5,
        width=width,
        color="#2b6cb0",
        label="Base (λ2 = 0,10/min)",
    )
    ax0.bar(
        [i + width / 2 for i in x],
        a_loss,
        yerr=a_loss_hw,
        capsize=3.5,
        width=width,
        color="#dd6b20",
        label="Escenario A (λ2 = 0,14/min)",
    )
    top_loss = max([v + h for v, h in zip(a_loss, a_loss_hw)] + [1.0])
    label_offset = max(top_loss * 0.03, 0.03)
    for idx, (b_val, a_val) in enumerate(zip(base_loss, a_loss)):
        ax0.text(idx - width / 2, b_val + base_loss_hw[idx] + label_offset, f"{b_val:.2f}%", ha="center", va="bottom", fontsize=7.5)
        ax0.text(idx + width / 2, a_val + a_loss_hw[idx] + label_offset, f"{a_val:.2f}%", ha="center", va="bottom", fontsize=7.5)
    ax0.set_xticks(x, loss_labels)
    ax0.set_ylabel("Probabilidad de bloqueo (%)")
    ax0.set_title("Tasa de pérdida (P_loss)")
    ax0.set_ylim(0, top_loss * 1.40)
    ax0.legend(loc="upper right", frameon=True, fontsize=8.0)

    # Panel B: Utilización efectiva vs ofrecida (%)
    ax1 = axes[1]
    labels_u = ["Base\n(λ2=0,10)", "Escenario A\n(λ2=0,14)"]
    eff_u = [
        100.0 * base["metrics"]["utilization"]["mean"],
        100.0 * scen_a["metrics"]["utilization"]["mean"],
    ]
    eff_hw = [
        100.0 * base["metrics"]["utilization"]["half_width"],
        100.0 * scen_a["metrics"]["utilization"]["half_width"],
    ]
    off_u = [
        100.0 * base["parameters"]["offered_utilization"],
        100.0 * scen_a["parameters"]["offered_utilization"],
    ]
    xu = [0, 1]
    ax1.bar(
        xu,
        eff_u,
        yerr=eff_hw,
        capsize=4,
        width=0.45,
        color=["#2b6cb0", "#dd6b20"],
        label="Utilización efectiva (IC95 %)",
    )
    ax1.scatter(xu, off_u, marker="D", s=55, color="#1a202c", zorder=5, label="Carga ofrecida teórica (ρ)")
    ax1.axhline(100.0, color="#c53030", linestyle="--", linewidth=1.2, label="Saturación (100 %)")
    for idx, val in enumerate(eff_u):
        top_u = max(val + eff_hw[idx], off_u[idx])
        ax1.text(idx, top_u + 2.5, f"{val:.1f}%", ha="center", va="bottom", fontsize=8.0)
    ax1.set_xticks(xu, labels_u)
    ax1.set_ylabel("Utilización conjunta (%)")
    ax1.set_ylim(0, 112)
    ax1.set_title("Utilización de los 3 analistas")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.8)

    # Panel C: Tiempos de espera y resolución
    ax2 = axes[2]
    time_keys = ["Wq1", "W1", "Wq2", "W2"]
    xt = list(range(len(time_keys)))
    base_t = [base["metrics"][k]["mean"] for k in time_keys]
    base_t_hw = [base["metrics"][k]["half_width"] for k in time_keys]
    a_t = [scen_a["metrics"][k]["mean"] for k in time_keys]
    a_t_hw = [scen_a["metrics"][k]["half_width"] for k in time_keys]

    ax2.bar(
        [i - width / 2 for i in xt],
        base_t,
        yerr=base_t_hw,
        capsize=3.5,
        width=width,
        color="#2b6cb0",
        label="Base",
    )
    ax2.bar(
        [i + width / 2 for i in xt],
        a_t,
        yerr=a_t_hw,
        capsize=3.5,
        width=width,
        color="#dd6b20",
        label="Escenario A",
    )
    ax2.set_xticks(xt, time_keys)
    ax2.set_ylabel("Minutos")
    ax2.set_title("Tiempos medios (solo admitidas)")
    ax2.legend(loc="upper left", frameon=True)

    fig.suptitle(
        "SOC — Escenario A: impacto del aumento de +40 % en alertas preventivas (30 réplicas, IC95 %)",
        fontsize=11.5,
        fontweight="bold",
    )
    outputs = _save_figure(fig, figures_dir, "soc_scenario_a")
    plt.close(fig)
    return outputs


def generate_soc_scenario_b_figure(
    results_dir: Path,
    figures_dir: Path,
) -> list[Path]:
    """Genera ``soc_scenario_b.{pdf,png}`` comparando K=16 vs. s=4 en ambos regímenes."""
    summary_path = results_dir / "soc_scenarios_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"No se encontró {summary_path}.")

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    scenarios = payload["scenarios"]

    plt = _load_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(14.4, 4.4))

    base_group = ("base", "scenario_b_k16", "scenario_b_s4")
    overload_group = ("scenario_a", "scenario_b_k16_overload", "scenario_b_s4_overload")
    config_labels = ["Actual\n(s=3, K=8)", "Ampliar buffer\n(s=3, K=16)", "4.º analista\n(s=4, K=8)"]
    x = [0, 1, 2]
    width = 0.35

    # Panel A: P_loss (%) bajo demanda base vs sobrecarga
    ax0 = axes[0]
    p_base = [100.0 * scenarios[sid]["metrics"]["P_loss"]["mean"] for sid in base_group]
    p_base_hw = [100.0 * scenarios[sid]["metrics"]["P_loss"]["half_width"] for sid in base_group]
    p_over = [100.0 * scenarios[sid]["metrics"]["P_loss"]["mean"] for sid in overload_group]
    p_over_hw = [100.0 * scenarios[sid]["metrics"]["P_loss"]["half_width"] for sid in overload_group]

    ax0.bar(
        [i - width / 2 for i in x],
        p_base,
        yerr=p_base_hw,
        capsize=3.5,
        width=width,
        color="#2b6cb0",
        label="Demanda base (λ2=0,10)",
    )
    ax0.bar(
        [i + width / 2 for i in x],
        p_over,
        yerr=p_over_hw,
        capsize=3.5,
        width=width,
        color="#c53030",
        label="Sobrecarga A (λ2=0,14)",
    )
    top_p = max([v + h for v, h in zip(p_over, p_over_hw)] + [1.0])
    p_offset = max(top_p * 0.03, 0.03)
    for idx, (b_val, o_val) in enumerate(zip(p_base, p_over)):
        ax0.text(idx - width / 2, b_val + p_base_hw[idx] + p_offset, f"{b_val:.2f}%", ha="center", va="bottom", fontsize=7.3)
        ax0.text(idx + width / 2, o_val + p_over_hw[idx] + p_offset, f"{o_val:.2f}%", ha="center", va="bottom", fontsize=7.3)
    ax0.set_xticks(x, config_labels)
    ax0.set_ylabel("Probabilidad de bloqueo P_loss (%)")
    ax0.set_title("Reducción de alertas perdidas")
    ax0.set_ylim(0, top_p * 1.28)
    ax0.legend(loc="upper right", frameon=True)

    # Panel B: Tiempos en cola Wq1 y Wq2 bajo demanda base
    ax1 = axes[1]
    wq1_base = [scenarios[sid]["metrics"]["Wq1"]["mean"] for sid in base_group]
    wq1_base_hw = [scenarios[sid]["metrics"]["Wq1"]["half_width"] for sid in base_group]
    wq2_base = [scenarios[sid]["metrics"]["Wq2"]["mean"] for sid in base_group]
    wq2_base_hw = [scenarios[sid]["metrics"]["Wq2"]["half_width"] for sid in base_group]

    ax1.bar(
        [i - width / 2 for i in x],
        wq1_base,
        yerr=wq1_base_hw,
        capsize=3.5,
        width=width,
        color="#3182ce",
        label="Wq1 (críticas)",
    )
    ax1.bar(
        [i + width / 2 for i in x],
        wq2_base,
        yerr=wq2_base_hw,
        capsize=3.5,
        width=width,
        color="#38a169",
        label="Wq2 (preventivas)",
    )
    ax1.set_xticks(x, config_labels)
    ax1.set_ylabel("Minutos en cola")
    ax1.set_title("Esperas en cola — Demanda base")
    ax1.legend(loc="upper right", frameon=True)

    # Panel C: Tiempos en cola Wq1 y Wq2 bajo sobrecarga A
    ax2 = axes[2]
    wq1_ov = [scenarios[sid]["metrics"]["Wq1"]["mean"] for sid in overload_group]
    wq1_ov_hw = [scenarios[sid]["metrics"]["Wq1"]["half_width"] for sid in overload_group]
    wq2_ov = [scenarios[sid]["metrics"]["Wq2"]["mean"] for sid in overload_group]
    wq2_ov_hw = [scenarios[sid]["metrics"]["Wq2"]["half_width"] for sid in overload_group]

    ax2.bar(
        [i - width / 2 for i in x],
        wq1_ov,
        yerr=wq1_ov_hw,
        capsize=3.5,
        width=width,
        color="#3182ce",
        label="Wq1 (críticas)",
    )
    ax2.bar(
        [i + width / 2 for i in x],
        wq2_ov,
        yerr=wq2_ov_hw,
        capsize=3.5,
        width=width,
        color="#38a169",
        label="Wq2 (preventivas)",
    )
    ax2.set_xticks(x, config_labels)
    ax2.set_ylabel("Minutos en cola")
    ax2.set_title("Esperas en cola — Sobrecarga A")
    ax2.legend(loc="upper right", frameon=True)

    fig.suptitle(
        "SOC — Escenario B: ampliar buffer (K=16) vs. contratar 4.º analista (s=4) (IC95 %)",
        fontsize=11.5,
        fontweight="bold",
    )
    outputs = _save_figure(fig, figures_dir, "soc_scenario_b")
    plt.close(fig)
    return outputs


def generate_soc_base_figure(
    results_dir: Path,
    figures_dir: Path,
) -> list[Path]:
    """Genera ``soc_base.{pdf,png}`` con las métricas del caso base."""
    summary_path = results_dir / "soc_base_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"No se encontró {summary_path}.")

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    parameters = payload["parameters"]

    plt = _load_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.4))

    # Panel A: probabilidad de bloqueo global y por tipo
    ax0 = axes[0]
    loss_keys = ["P_loss", "P_loss1", "P_loss2"]
    loss_labels = ["Global", "Críticas (T1)", "Preventivas (T2)"]
    loss_values = [100.0 * metrics[k]["mean"] for k in loss_keys]
    loss_hw = [100.0 * metrics[k]["half_width"] for k in loss_keys]
    x = list(range(len(loss_keys)))
    ax0.bar(x, loss_values, yerr=loss_hw, capsize=4, width=0.55, color="#2b6cb0", alpha=0.85)
    for idx, value in enumerate(loss_values):
        ax0.text(
            idx,
            value + loss_hw[idx] + 0.03,
            f"{value:.3f}%",
            ha="center",
            va="bottom",
            fontsize=8.0,
        )
    ax0.set_xticks(x, loss_labels)
    ax0.set_ylabel("Probabilidad de bloqueo (%)")
    ax0.set_title("Pérdida de alertas (P_loss)")
    ax0.set_ylim(0, max(v + h for v, h in zip(loss_values, loss_hw)) * 1.45)

    # Panel B: utilización efectiva frente a carga ofrecida
    ax1 = axes[1]
    effective = 100.0 * metrics["utilization"]["mean"]
    effective_hw = 100.0 * metrics["utilization"]["half_width"]
    offered = 100.0 * parameters["offered_utilization"]
    ax1.bar(
        [0],
        [effective],
        yerr=[effective_hw],
        capsize=5,
        width=0.42,
        color="#2f855a",
        label="Utilización efectiva (IC95 %)",
    )
    ax1.scatter([0], [offered], marker="D", s=55, color="#1a202c", zorder=5, label="Carga ofrecida teórica")
    ax1.axhline(100.0, color="#c53030", linestyle="--", linewidth=1.2, label="Saturación (100 %)")
    ax1.text(0, effective + effective_hw + 2.0, f"{effective:.2f}%", ha="center", va="bottom", fontsize=8.0)
    ax1.set_xticks([0], ["Caso base"])
    ax1.set_ylabel("Utilización conjunta (%)")
    ax1.set_xlim(-0.7, 0.7)
    ax1.set_ylim(0, 112)
    ax1.set_title("Utilización de los 3 analistas")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.5)

    # Panel C: tiempos medios de espera y resolución
    ax2 = axes[2]
    time_keys = ["Wq1", "W1", "Wq2", "W2"]
    time_values = [metrics[k]["mean"] for k in time_keys]
    time_hw = [metrics[k]["half_width"] for k in time_keys]
    xt = list(range(len(time_keys)))
    ax2.bar(xt, time_values, yerr=time_hw, capsize=4, width=0.55, color="#dd6b20", alpha=0.85)
    for idx, value in enumerate(time_values):
        ax2.text(
            idx,
            value + time_hw[idx] + 0.4,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8.0,
        )
    ax2.set_xticks(xt, ["Wq1", "W1", "Wq2", "W2"])
    ax2.set_ylabel("Minutos")
    ax2.set_title("Tiempos medios (solo admitidas)")
    ax2.set_ylim(0, max(v + h for v, h in zip(time_values, time_hw)) * 1.25)

    fig.suptitle(
        f"SOC — Caso base (s=3, K=8, λ2=0,10/min; {payload['design']['replications']} réplicas, IC95 %)",
        fontsize=11.5,
        fontweight="bold",
    )
    outputs = _save_figure(fig, figures_dir, "soc_base")
    plt.close(fig)
    return outputs


def generate_all_figures(
    results_dir: Path = Path("results"),
    figures_dir: Path = Path("figures"),
) -> list[Path]:
    """Genera todas las figuras disponibles a partir de los resultados existentes."""
    generated: list[Path] = []
    if (results_dir / "mm1_summary.json").is_file():
        generated.extend(generate_mm1_validation_figure(results_dir, figures_dir))
    if (results_dir / "soc_base_summary.json").is_file():
        generated.extend(generate_soc_base_figure(results_dir, figures_dir))
    if (results_dir / "soc_scenarios_summary.json").is_file():
        generated.extend(generate_soc_scenario_a_figure(results_dir, figures_dir))
        generated.extend(generate_soc_scenario_b_figure(results_dir, figures_dir))
    if not generated:
        raise FileNotFoundError(
            f"No se encontraron resúmenes JSON en {results_dir} para generar figuras."
        )
    return generated
