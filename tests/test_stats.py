from __future__ import annotations

import pytest

from simulacion_colas.stats import (
    TimeWeightedAccumulator,
    little_ratio,
    mean_or_zero,
    paired_difference,
    relative_change,
    student_t_cdf,
    summarize,
    t_critical,
)


def test_time_weighted_accumulator_computes_area_and_mean() -> None:
    accumulator = TimeWeightedAccumulator(start_time=0.0, initial_value=0.0)

    accumulator.update(2.0, 4.0)
    accumulator.update(5.0, 2.0)

    assert accumulator.area() == pytest.approx(12.0)
    assert accumulator.area(6.0) == pytest.approx(14.0)
    assert accumulator.mean(6.0) == pytest.approx(14.0 / 6.0)


def test_time_weighted_accumulator_rejects_time_going_backwards() -> None:
    accumulator = TimeWeightedAccumulator()
    accumulator.update(5.0, 1.0)

    with pytest.raises(ValueError, match="retroceder"):
        accumulator.update(4.0, 2.0)

    with pytest.raises(ValueError, match="anterior"):
        accumulator.area(4.0)


@pytest.mark.parametrize(
    ("degrees", "expected"),
    [
        (1, 12.7062),
        (5, 2.5706),
        (10, 2.2281),
        (30, 2.0423),
        (1000, 1.9623),
    ],
)
def test_t_critical_matches_reference_values(degrees: int, expected: float) -> None:
    assert t_critical(0.95, degrees) == pytest.approx(expected, abs=1e-3)


def test_student_t_cdf_is_symmetric() -> None:
    assert student_t_cdf(0.0, 10) == pytest.approx(0.5)
    assert student_t_cdf(2.0, 10) == pytest.approx(1.0 - student_t_cdf(-2.0, 10))


def test_summarize_reports_mean_and_interval() -> None:
    summary = summarize([1.0, 2.0, 3.0, 4.0, 5.0])

    assert summary.n == 5
    assert summary.mean == pytest.approx(3.0)
    assert summary.stdev == pytest.approx(1.5811, abs=1e-4)
    assert summary.half_width == pytest.approx(1.9632, abs=1e-3)
    assert summary.lower == pytest.approx(1.0368, abs=1e-3)
    assert summary.upper == pytest.approx(4.9632, abs=1e-3)
    assert summary.relative_error == pytest.approx(summary.half_width / 3.0)
    assert summary.contains(3.0)
    assert not summary.contains(10.0)


def test_summarize_requires_two_observations() -> None:
    with pytest.raises(ValueError, match="al menos dos"):
        summarize([1.0])


def test_little_ratio_is_one_when_relation_holds() -> None:
    assert little_ratio(level=3.0, arrival_rate=0.25, time_in_system=12.0) == pytest.approx(1.0)
    assert little_ratio(level=2.25, arrival_rate=0.25, time_in_system=9.0) == pytest.approx(1.0)


def test_paired_difference_uses_after_minus_before() -> None:
    result = paired_difference([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])

    assert result.n == 3
    assert result.mean == pytest.approx(2.0)


def test_paired_difference_requires_equal_sizes() -> None:
    with pytest.raises(ValueError, match="mismo tamaño"):
        paired_difference([1.0, 2.0], [1.0])


def test_relative_change_and_mean_or_zero() -> None:
    assert relative_change(0.02, 0.03) == pytest.approx(0.5)
    assert mean_or_zero([]) == 0.0
    assert mean_or_zero([2.0, 4.0]) == pytest.approx(3.0)
