from __future__ import annotations

import csv
import json
from math import gamma
from pathlib import Path

import pytest

from simulacion_colas.cli import main
from simulacion_colas.soc import (
    DEFAULT_SOC_DURATION,
    DEFAULT_SOC_HORIZON,
    DEFAULT_SOC_WARMUP,
    OVERLOAD_ARRIVAL_RATE_2,
    SOCParameters,
    SOCScriptedArrival,
    run_soc_replications,
    run_soc_scenarios,
    simulate_soc_replication,
    simulate_soc_scripted,
    summarize_soc_replications,
)


def test_soc_parameters_match_statement() -> None:
    params = SOCParameters()

    assert params.analysts == 3
    assert params.queue_capacity == 8
    assert params.system_capacity == 11
    assert params.arrival_rate_1 == pytest.approx(0.05)
    assert params.arrival_rate_2 == pytest.approx(0.10)
    assert params.mean_service_1 == pytest.approx(20.0)
    assert params.mean_service_2 == pytest.approx(12.0 * gamma(1.0 + 1.0 / 1.5))
    assert params.mean_service_2 == pytest.approx(10.8329, abs=1e-4)
    assert params.theoretically_unsaturated


@pytest.mark.parametrize(
    "kwargs",
    [
        {"analysts": 0},
        {"queue_capacity": -1},
        {"arrival_rate_1": 0.0},
        {"arrival_rate_2": -0.1},
        {"service_1_low": 25.0, "service_1_high": 25.0},
        {"service_2_shape": 0.0},
        {"service_2_scale": -2.0},
    ],
)
def test_soc_parameters_reject_invalid_values(kwargs: dict[str, float | int]) -> None:
    with pytest.raises(ValueError):
        SOCParameters(**kwargs)


def test_never_more_than_three_simultaneous_services() -> None:
    # Ráfaga determinista de 15 llegadas simultáneas
    burst = [SOCScriptedArrival(time=0.0, alert_type=1 if i % 2 == 0 else 2, service_duration=10.0) for i in range(15)]
    rep, records = simulate_soc_scripted(SOCParameters(), burst, warmup=0.0, horizon=50.0)

    assert rep.max_busy_analysts == 3
    assert rep.max_queue_length == 8
    assert len(records) == 11

    # Y durante 30 días estocásticos completos (incluso con sobrecarga)
    stochastic = simulate_soc_replication(
        SOCParameters(arrival_rate_2=OVERLOAD_ARRIVAL_RATE_2),
        seed=7,
    )
    assert stochastic.max_busy_analysts <= 3
    assert stochastic.max_queue_length <= 8


def test_blocks_when_three_analysts_busy_and_eight_in_queue() -> None:
    arrivals: list[SOCScriptedArrival] = []
    # 3 alertas ocupan a los 3 analistas hasta t=50
    for idx in range(3):
        arrivals.append(SOCScriptedArrival(time=0.1 * idx, alert_type=2, service_duration=50.0))
    # 8 alertas llenan los K=8 espacios de cola
    for idx in range(8):
        arrivals.append(SOCScriptedArrival(time=1.0 + idx, alert_type=2, service_duration=10.0))
    # La alerta 12 llega con el sistema lleno (3 en servicio + 8 en cola)
    arrivals.append(SOCScriptedArrival(time=9.5, alert_type=2, service_duration=10.0))

    rep, _ = simulate_soc_scripted(SOCParameters(), arrivals, warmup=0.0, horizon=100.0)

    assert rep.max_busy_analysts == 3
    assert rep.max_queue_length == 8
    assert rep.arrivals == 12
    assert rep.admitted == 11
    assert rep.blocked == 1
    assert rep.blocked_2 == 1
    assert rep.completed == 11
    assert rep.P_loss == pytest.approx(1.0 / 12.0)


def test_critical_alert_is_blocked_when_queue_is_full() -> None:
    arrivals: list[SOCScriptedArrival] = []
    # 3 preventivas en servicio (t=0..0.2) + 8 preventivas en cola (t=1..8)
    for idx in range(3):
        arrivals.append(SOCScriptedArrival(time=0.1 * idx, alert_type=2, service_duration=40.0))
    for idx in range(8):
        arrivals.append(SOCScriptedArrival(time=1.0 + idx, alert_type=2, service_duration=5.0))
    # Alerta crítica llega con cola llena en t=9.0 -> debe ser rechazada sin desalojar preventivas
    arrivals.append(SOCScriptedArrival(time=9.0, alert_type=1, service_duration=20.0))

    rep, records = simulate_soc_scripted(SOCParameters(), arrivals, warmup=0.0, horizon=100.0)

    assert rep.arrivals_1 == 1
    assert rep.admitted_1 == 0
    assert rep.blocked_1 == 1
    assert rep.P_loss1 == pytest.approx(1.0)
    assert rep.arrivals_2 == 11
    assert rep.admitted_2 == 11
    assert rep.blocked_2 == 0
    assert rep.completed_2 == 11
    assert all(rec.alert_type == 2 for rec in records)


def test_critical_has_priority_over_preventive_when_analyst_frees() -> None:
    arrivals = [
        # 3 analistas ocupados hasta t=20.0, 20.1, 20.2
        SOCScriptedArrival(time=0.0, alert_type=2, service_duration=20.0),
        SOCScriptedArrival(time=0.1, alert_type=2, service_duration=20.0),
        SOCScriptedArrival(time=0.2, alert_type=2, service_duration=20.0),
        # Llega primero preventiva en t=1.0, luego crítica en t=2.0
        SOCScriptedArrival(time=1.0, alert_type=2, service_duration=5.0),
        SOCScriptedArrival(time=2.0, alert_type=1, service_duration=5.0),
    ]

    rep, records = simulate_soc_scripted(SOCParameters(), arrivals, warmup=0.0, horizon=100.0)

    queued_starts = sorted(
        (rec for rec in records if rec.arrival_time >= 1.0),
        key=lambda rec: (rec.start_time, rec.alert_id),
    )
    assert [rec.alert_type for rec in queued_starts] == [1, 2]
    assert queued_starts[0].start_time == pytest.approx(20.0)
    assert queued_starts[1].start_time == pytest.approx(20.1)
    assert rep.Wq1 == pytest.approx(18.0)
    assert rep.Wq2 == pytest.approx((0.0 * 3 + 19.1) / 4.0)


def test_non_preemptive_priority_does_not_interrupt_service() -> None:
    arrivals = [
        # 3 preventivas ocupan a todos los analistas desde t=0 hasta t=30.0, 30.1, 30.2
        SOCScriptedArrival(time=0.0, alert_type=2, service_duration=30.0),
        SOCScriptedArrival(time=0.1, alert_type=2, service_duration=30.0),
        SOCScriptedArrival(time=0.2, alert_type=2, service_duration=30.0),
        # Crítica llega en t=1.0: no debe expropiar ninguna preventiva en curso
        SOCScriptedArrival(time=1.0, alert_type=1, service_duration=10.0),
    ]

    rep, records = simulate_soc_scripted(SOCParameters(), arrivals, warmup=0.0, horizon=100.0)

    initial_preventives = [rec for rec in records if rec.arrival_time < 0.5]
    critical = next(rec for rec in records if rec.alert_type == 1)

    assert [rec.departure_time for rec in initial_preventives] == pytest.approx([30.0, 30.1, 30.2])
    assert critical.start_time == pytest.approx(30.0)
    assert critical.departure_time == pytest.approx(40.0)
    assert rep.Wq1 == pytest.approx(29.0)
    assert rep.W1 == pytest.approx(39.0)


def test_fifo_within_each_class() -> None:
    arrivals = [
        # 3 analistas ocupados hasta t=20.0, 20.1, 20.2
        SOCScriptedArrival(time=0.0, alert_type=2, service_duration=20.0),
        SOCScriptedArrival(time=0.1, alert_type=2, service_duration=20.0),
        SOCScriptedArrival(time=0.2, alert_type=2, service_duration=20.0),
        # Intercalamos preventivas y críticas en cola
        SOCScriptedArrival(time=1.0, alert_type=2, service_duration=5.0),
        SOCScriptedArrival(time=2.0, alert_type=1, service_duration=5.0),
        SOCScriptedArrival(time=3.0, alert_type=2, service_duration=5.0),
        SOCScriptedArrival(time=4.0, alert_type=1, service_duration=5.0),
        SOCScriptedArrival(time=5.0, alert_type=2, service_duration=5.0),
        SOCScriptedArrival(time=6.0, alert_type=1, service_duration=5.0),
    ]

    _, records = simulate_soc_scripted(SOCParameters(), arrivals, warmup=0.0, horizon=100.0)

    queued = sorted(
        (rec for rec in records if rec.arrival_time >= 1.0),
        key=lambda rec: (rec.start_time, rec.alert_id),
    )
    assert [(rec.alert_type, rec.arrival_time) for rec in queued] == [
        (1, 2.0),
        (1, 4.0),
        (1, 6.0),
        (2, 1.0),
        (2, 3.0),
        (2, 5.0),
    ]


@pytest.mark.parametrize("drain", [True, False])
def test_conservation_invariants(drain: bool) -> None:
    for seed in (1, 5):
        rep = simulate_soc_replication(
            SOCParameters(arrival_rate_2=OVERLOAD_ARRIVAL_RATE_2),
            seed=seed,
            warmup=200.0,
            horizon=3_000.0,
            drain=drain,
        )
        assert rep.arrivals == rep.arrivals_1 + rep.arrivals_2
        assert rep.admitted == rep.admitted_1 + rep.admitted_2
        assert rep.blocked == rep.blocked_1 + rep.blocked_2
        assert rep.completed == rep.completed_1 + rep.completed_2
        assert rep.remaining == rep.remaining_1 + rep.remaining_2

        assert rep.arrivals_1 == rep.admitted_1 + rep.blocked_1
        assert rep.arrivals_2 == rep.admitted_2 + rep.blocked_2
        assert rep.arrivals == rep.admitted + rep.blocked

        assert rep.admitted_1 == rep.completed_1 + rep.remaining_1
        assert rep.admitted_2 == rep.completed_2 + rep.remaining_2
        assert rep.admitted == rep.completed + rep.remaining

        if drain:
            assert rep.remaining == 0
            assert rep.remaining_1 == 0
            assert rep.remaining_2 == 0
            assert rep.completed == rep.admitted

        assert 0.0 <= rep.utilization <= 1.0
        assert 0.0 <= rep.P_loss <= 1.0
        assert rep.Lq == pytest.approx(rep.Lq1 + rep.Lq2)
        assert rep.W1 >= rep.Wq1
        assert rep.W2 >= rep.Wq2


def test_soc_reproducibility_and_full_30_day_run() -> None:
    first = simulate_soc_replication(seed=1)
    second = simulate_soc_replication(seed=1)
    other = simulate_soc_replication(seed=2)

    assert first == second
    assert first != other
    assert first.warmup == DEFAULT_SOC_WARMUP
    assert first.horizon == DEFAULT_SOC_HORIZON
    assert first.duration == DEFAULT_SOC_DURATION
    assert first.arrivals > 5_000
    assert first.remaining == 0


def test_soc_scenarios_use_common_random_numbers_and_compare_pairs() -> None:
    suite = run_soc_scenarios(
        replications=4,
        base_seed=10,
        warmup=200.0,
        horizon=2_500.0,
    )

    expected_ids = {
        "base",
        "scenario_a",
        "scenario_b_k16",
        "scenario_b_s4",
        "scenario_b_k16_overload",
        "scenario_b_s4_overload",
    }
    assert set(suite.summaries) == expected_ids

    # Semillas comunes (CRN): mismas llegadas para misma demanda y flujos independientes
    for idx in range(4):
        base_run = suite.replications_by_scenario["base"][idx]
        scen_a_run = suite.replications_by_scenario["scenario_a"][idx]
        k16_run = suite.replications_by_scenario["scenario_b_k16"][idx]
        s4_run = suite.replications_by_scenario["scenario_b_s4"][idx]

        assert base_run.arrivals_1 == scen_a_run.arrivals_1
        assert base_run.arrivals_1 == k16_run.arrivals_1 == s4_run.arrivals_1
        assert base_run.arrivals_2 == k16_run.arrivals_2 == s4_run.arrivals_2

    assert suite.summaries["scenario_a"].parameters.arrival_rate_2 == pytest.approx(0.14)
    assert suite.recommendation
    assert len(suite.comparisons) > 0


def test_soc_and_scenarios_cli_exports_and_figures(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    figures_dir = tmp_path / "figures"

    # Ejecución rápida del CLI para soc, scenarios y figures
    assert main(
        [
            "soc",
            "--reps",
            "3",
            "--warmup-min",
            "100",
            "--horizon-min",
            "1500",
            "--results-dir",
            str(results_dir),
        ]
    ) == 0

    for filename in ("soc_base_replicas.csv", "soc_base_summary.csv", "soc_base_summary.json"):
        assert (results_dir / filename).is_file()

    assert main(
        [
            "scenarios",
            "--reps",
            "3",
            "--warmup-min",
            "100",
            "--horizon-min",
            "1500",
            "--results-dir",
            str(results_dir),
            "--figures-dir",
            str(figures_dir),
        ]
    ) == 0

    for filename in (
        "soc_scenarios_replicas.csv",
        "soc_scenarios_summary.csv",
        "soc_scenarios_comparisons.csv",
        "soc_scenarios_summary.json",
    ):
        assert (results_dir / filename).is_file()

    for fig_name in ("soc_base.pdf", "soc_base.png", "soc_scenario_a.pdf", "soc_scenario_a.png", "soc_scenario_b.pdf", "soc_scenario_b.png"):
        assert (figures_dir / fig_name).is_file()

    # Verificar el subcomando figures de forma independiente
    fig_only_dir = tmp_path / "figures_only"
    assert main(
        [
            "figures",
            "--results-dir",
            str(results_dir),
            "--figures-dir",
            str(fig_only_dir),
        ]
    ) == 0
    for fig_name in ("soc_base.pdf", "soc_base.png", "soc_scenario_a.pdf", "soc_scenario_a.png", "soc_scenario_b.pdf", "soc_scenario_b.png"):
        assert (fig_only_dir / fig_name).is_file()

    with (results_dir / "soc_scenarios_replicas.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 6 * 3

    payload = json.loads((results_dir / "soc_scenarios_summary.json").read_text(encoding="utf-8"))
    assert payload["model"] == "SOC"
    assert payload["design"]["common_random_numbers"] is True

    # Verificar el subcomando summarize_soc_replications / run_soc_replications
    runs = run_soc_replications(replications=2, warmup=100.0, horizon=1000.0)
    summary = summarize_soc_replications(runs)
    assert summary.replications == 2


def test_versioned_soc_results_and_figures_are_consistent() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    results_dir = repo_root / "results"
    figures_dir = repo_root / "figures"

    summary_json = json.loads((results_dir / "soc_scenarios_summary.json").read_text(encoding="utf-8"))
    base_json = json.loads((results_dir / "soc_base_summary.json").read_text(encoding="utf-8"))

    assert summary_json["scenarios"]["base"]["metrics"] == base_json["metrics"]

    with (results_dir / "soc_scenarios_summary.csv").open(encoding="utf-8", newline="") as file:
        csv_rows = list(csv.DictReader(file))

    for row in csv_rows:
        sid = row["scenario_id"]
        metric = row["metric"]
        expected_mean = summary_json["scenarios"][sid]["metrics"][metric]["mean"]
        assert float(row["mean"]) == pytest.approx(expected_mean)

    for fig_name in (
        "mm1_validation.pdf",
        "mm1_validation.png",
        "soc_base.pdf",
        "soc_base.png",
        "soc_scenario_a.pdf",
        "soc_scenario_a.png",
        "soc_scenario_b.pdf",
        "soc_scenario_b.png",
    ):
        assert (figures_dir / fig_name).is_file()

