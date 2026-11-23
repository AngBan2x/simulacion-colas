from __future__ import annotations

from math import gamma
from random import Random

import pytest

from simulacion_colas.distributions import (
    Exponential,
    Uniform,
    Weibull,
    spawn_streams,
)


def test_exponential_has_expected_mean() -> None:
    distribution = Exponential(rate=0.25)
    rng = Random(2026)

    samples = [distribution.sample(rng) for _ in range(20_000)]

    assert distribution.mean() == pytest.approx(4.0)
    assert sum(samples) / len(samples) == pytest.approx(4.0, rel=0.03)
    assert all(sample >= 0.0 for sample in samples)


def test_uniform_stays_within_bounds() -> None:
    distribution = Uniform(low=15.0, high=25.0)
    rng = Random(7)

    samples = [distribution.sample(rng) for _ in range(10_000)]

    assert distribution.mean() == pytest.approx(20.0)
    assert all(15.0 <= sample <= 25.0 for sample in samples)
    assert sum(samples) / len(samples) == pytest.approx(20.0, rel=0.01)


def test_weibull_matches_theoretical_mean() -> None:
    distribution = Weibull(shape=1.5, scale=12.0)
    rng = Random(11)

    samples = [distribution.sample(rng) for _ in range(20_000)]
    expected = 12.0 * gamma(1.0 + 1.0 / 1.5)

    assert expected == pytest.approx(10.8329, abs=1e-4)
    assert distribution.mean() == pytest.approx(expected)
    assert sum(samples) / len(samples) == pytest.approx(expected, rel=0.02)
    assert all(sample >= 0.0 for sample in samples)


def test_same_seed_reproduces_the_same_sequence() -> None:
    distribution = Weibull(shape=1.5, scale=12.0)

    first = [distribution.sample(Random(99)) for _ in range(3)]
    second = [distribution.sample(Random(99)) for _ in range(3)]

    assert first == second


def test_spawn_streams_is_deterministic_and_independent() -> None:
    first = spawn_streams(1234, ["llegadas", "servicios"])
    second = spawn_streams(1234, ["llegadas", "servicios"])

    arrivals_a = [first["llegadas"].random() for _ in range(20)]
    arrivals_b = [second["llegadas"].random() for _ in range(20)]
    services_a = [first["servicios"].random() for _ in range(20)]
    services_b = [second["servicios"].random() for _ in range(20)]

    assert arrivals_a == arrivals_b
    assert services_a == services_b
    assert arrivals_a != services_a


def test_spawn_streams_requires_unique_names() -> None:
    with pytest.raises(ValueError, match="únicos"):
        spawn_streams(1, ["a", "a"])

    with pytest.raises(ValueError, match="al menos un nombre"):
        spawn_streams(1, [])


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Exponential(rate=0.0),
        lambda: Uniform(low=5.0, high=5.0),
        lambda: Weibull(shape=-1.0, scale=12.0),
    ],
)
def test_invalid_parameters_are_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory()
