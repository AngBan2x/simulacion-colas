from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from simulacion_colas.cli import main
from simulacion_colas.mm1 import (
    MM1Analytical,
    MM1Parameters,
    recommend_warmup,
    run_replications,
    run_warmup_pilot,
    simulate_replication,
    summarize_replications,
)


def test_analytical_values_match_the_statement() -> None:
    parameters = MM1Parameters()
    analytical = MM1Analytical.from_parameters(parameters)

    assert parameters.arrival_rate == pytest.approx(0.25)
    assert parameters.service_rate == pytest.approx(1.0 / 3.0)
    assert parameters.utilization == pytest.approx(0.75)
    assert parameters.stable

    assert analytical.rho == pytest.approx(0.75)
    assert analytical.L == pytest.approx(3.0)
    assert analytical.Lq == pytest.approx(2.25)
    assert analytical.W == pytest.approx(12.0)
    assert analytical.Wq == pytest.approx(9.0)
    assert analytical.probability_of_n(0) == pytest.approx(0.25)


def test_unstable_parameters_have_no_analytical_solution() -> None:
    parameters = MM1Parameters(arrival_rate=0.5, service_rate=0.5)

    assert not parameters.stable
    with pytest.raises(ValueError, match="ρ < 1"):
        MM1Analytical.from_parameters(parameters)
    with pytest.raises(ValueError, match="ρ < 1"):
        simulate_replication(parameters)


def test_replication_is_reproducible_and_consistent() -> None:
    first = simulate_replication(seed=1)
    second = simulate_replication(seed=1)
    other = simulate_replication(seed=2)

    assert first == second
    assert first != other

    assert first.arrivals > 0
    assert first.completed == first.arrivals
    assert 0.0 <= first.utilization <= 1.0
    assert first.L >= first.Lq
    assert first.W >= first.Wq
    assert abs(first.little_l - 1.0) < 0.01
    assert abs(first.little_lq - 1.0) < 0.01


def test_fifty_replications_cover_the_analytical_values() -> None:
    replications = run_replications(replications=50)
    summary = summarize_replications(replications)

    assert summary.replications == 50
    assert summary.all_intervals_contain_analytical
    assert summary.little_L == pytest.approx(1.0, abs=0.01)
    assert summary.little_Lq == pytest.approx(1.0, abs=0.01)

    for metric in summary.metrics.values():
        assert metric.confidence_interval.lower <= metric.confidence_interval.mean
        assert metric.confidence_interval.mean <= metric.confidence_interval.upper


def test_summary_requires_at_least_two_replications() -> None:
    with pytest.raises(ValueError, match="al menos dos"):
        summarize_replications([simulate_replication(seed=1)])


def test_warmup_pilot_reports_recommendation() -> None:
    rows = run_warmup_pilot(
        candidates=(0.0, 500.0),
        replications=2,
        base_seed=3,
        horizon=6_000.0,
    )

    assert len(rows) == 2
    assert rows[0].warmup == 0.0
    assert rows[1].relative_L == 0.0
    assert rows[1].relative_W == 0.0
    assert recommend_warmup(rows) in (0.0, 500.0)


def test_cli_exports_replication_and_summary_files(tmp_path: Path) -> None:
    exit_code = main(
        [
            "mm1",
            "--replications",
            "4",
            "--warmup",
            "300",
            "--horizon",
            "4_000",
            "--seed",
            "1",
            "--results-dir",
            str(tmp_path),
            "--pilot-replications",
            "2",
        ]
    )

    assert exit_code == 0
    for name in (
        "mm1_replicas.csv",
        "mm1_summary.csv",
        "mm1_summary.json",
        "mm1_warmup_pilot.csv",
    ):
        assert (tmp_path / name).is_file()

    with (tmp_path / "mm1_replicas.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 4
    assert rows[0]["seed"] == "1"

    payload = json.loads((tmp_path / "mm1_summary.json").read_text(encoding="utf-8"))
    assert payload["model"] == "M/M/1"
    assert payload["design"]["replications"] == 4
    assert set(payload["metrics"]) == {"L", "Lq", "W", "Wq", "utilization"}
    assert set(payload["little"]) == {"L", "Lq"}
