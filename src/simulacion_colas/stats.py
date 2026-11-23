"""Acumuladores y estadística inferencial para los experimentos.

El módulo usa solo la biblioteca estándar. Incluye:

- acumuladores de área para promedios ponderados por tiempo;
- resúmenes con media, desviación estándar e intervalo de confianza del 95 %
  basado en la distribución t de Student;
- error relativo, ratios de Little y comparaciones pareadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, fsum, isfinite, lgamma, log, sqrt
from statistics import fmean, stdev
from typing import Iterable, Sequence


def _as_floats(values: Iterable[float]) -> list[float]:
    data = [float(value) for value in values]
    for value in data:
        if not isfinite(value):
            raise ValueError("Las observaciones deben ser valores finitos.")
    return data


@dataclass(slots=True)
class TimeWeightedAccumulator:
    """Promedio ponderado por tiempo de un nivel que cambia por eventos.

    El acumulador guarda el área bajo la curva entre actualizaciones. Para
    obtener el promedio de ``L`` o ``Lq`` basta con actualizarlo cada vez que
    cambia el número de clientes y consultar ``mean`` al final del horizonte.
    """

    start_time: float = 0.0
    initial_value: float = 0.0
    _last_time: float = 0.0
    _last_value: float = 0.0
    _area: float = 0.0

    def __post_init__(self) -> None:
        start = float(self.start_time)
        if not isfinite(start) or start < 0:
            raise ValueError("El tiempo inicial debe ser finito y no negativo.")
        self.start_time = start
        self._last_time = start
        self._last_value = float(self.initial_value)

    def update(self, time: float, value: float) -> None:
        """Registra un cambio de nivel en el instante ``time``."""
        moment = float(time)
        level = float(value)
        if not isfinite(moment):
            raise ValueError("El tiempo debe ser finito.")
        if moment < self._last_time:
            raise ValueError("El tiempo no puede retroceder.")
        if level < 0:
            raise ValueError("El nivel no puede ser negativo.")
        self._area += (moment - self._last_time) * self._last_value
        self._last_time = moment
        self._last_value = level

    def area(self, until: float | None = None) -> float:
        """Área acumulada hasta ``until`` (o hasta la última actualización)."""
        if until is None:
            return self._area
        limit = float(until)
        if limit < self._last_time:
            raise ValueError("El límite no puede ser anterior a la última actualización.")
        return self._area + (limit - self._last_time) * self._last_value

    def mean(self, until: float | None = None) -> float:
        """Nivel promedio en el intervalo transcurrido."""
        end = self._last_time if until is None else float(until)
        duration = end - self.start_time
        if duration <= 0:
            raise ValueError("El intervalo debe tener duración positiva.")
        return self.area(end) / duration


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """Resumen de una muestra con intervalo de confianza bilateral."""

    n: int
    mean: float
    stdev: float
    half_width: float
    lower: float
    upper: float
    relative_error: float
    confidence: float

    def contains(self, value: float) -> bool:
        """Indica si ``value`` cae dentro del intervalo."""
        return self.lower <= value <= self.upper


def _betacf(a: float, b: float, x: float) -> float:
    """Fracción continua de Lentz para la función beta incompleta."""
    max_iterations = 300
    epsilon = 3.0e-14
    tiny = 1.0e-300

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d

    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < epsilon:
            break

    return h


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """Función beta incompleta regularizada ``I_x(a, b)``."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    log_front = (
        lgamma(a + b)
        - lgamma(a)
        - lgamma(b)
        + a * log(x)
        + b * log(1.0 - x)
    )
    try:
        front = exp(log_front)
    except OverflowError:
        front = float("inf")

    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(value: float, degrees_of_freedom: float) -> float:
    """Función de distribución acumulada de la t de Student."""
    if degrees_of_freedom <= 0:
        raise ValueError("Los grados de libertad deben ser positivos.")
    x = float(value)
    if not isfinite(x):
        raise ValueError("El valor debe ser finito.")

    df = float(degrees_of_freedom)
    if x == 0.0:
        return 0.5
    tail = 0.5 * _regularized_incomplete_beta(df / 2.0, 0.5, df / (df + x * x))
    return 1.0 - tail if x > 0 else tail


def student_t_quantile(probability: float, degrees_of_freedom: float) -> float:
    """Cuantil de la t de Student mediante bisección sobre la CDF."""
    p = float(probability)
    if not 0.0 < p < 1.0:
        raise ValueError("La probabilidad debe estar estrictamente entre 0 y 1.")
    if degrees_of_freedom <= 0:
        raise ValueError("Los grados de libertad deben ser positivos.")
    if p == 0.5:
        return 0.0

    if p < 0.5:
        return -student_t_quantile(1.0 - p, degrees_of_freedom)

    low, high = 0.0, 1.0
    while student_t_cdf(high, degrees_of_freedom) < p:
        high *= 2.0
        if high > 1.0e12:
            raise RuntimeError("No se pudo acotar el cuantil de la t de Student.")

    for _ in range(200):
        middle = (low + high) / 2.0
        if student_t_cdf(middle, degrees_of_freedom) < p:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def t_critical(confidence: float = 0.95, degrees_of_freedom: int = 1) -> float:
    """Valor crítico bilateral ``t`` para el nivel de confianza indicado."""
    level = float(confidence)
    if not 0.0 < level < 1.0:
        raise ValueError("La confianza debe estar estrictamente entre 0 y 1.")
    if degrees_of_freedom < 1:
        raise ValueError("Se requiere al menos un grado de libertad.")
    return student_t_quantile(1.0 - (1.0 - level) / 2.0, float(degrees_of_freedom))


def summarize(
    values: Iterable[float],
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """Resume una muestra independiente con un IC bilateral para la media."""
    data = _as_floats(values)
    if len(data) < 2:
        raise ValueError("Se requieren al menos dos observaciones.")

    mean = fmean(data)
    deviation = stdev(data)
    critical = t_critical(confidence, len(data) - 1)
    half_width = critical * deviation / sqrt(len(data))
    relative = half_width / abs(mean) if mean != 0.0 else float("inf")

    return ConfidenceInterval(
        n=len(data),
        mean=mean,
        stdev=deviation,
        half_width=half_width,
        lower=mean - half_width,
        upper=mean + half_width,
        relative_error=relative,
        confidence=float(confidence),
    )


def little_ratio(level: float, arrival_rate: float, time_in_system: float) -> float:
    """Ratio ``L / (λ·W)``; debe ser cercano a 1 si se cumple Little."""
    rate = float(arrival_rate)
    if rate <= 0:
        raise ValueError("La tasa de llegadas debe ser positiva.")
    expected = rate * float(time_in_system)
    if expected == 0.0:
        raise ValueError("El producto λ·W debe ser distinto de cero.")
    return float(level) / expected


def paired_difference(
    before: Sequence[float],
    after: Sequence[float],
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """IC de la diferencia ``after - before`` para réplicas emparejadas."""
    first = _as_floats(before)
    second = _as_floats(after)
    if len(first) != len(second):
        raise ValueError("Las muestras pareadas deben tener el mismo tamaño.")
    return summarize(
        [b - a for a, b in zip(first, second, strict=True)],
        confidence=confidence,
    )


def relative_change(baseline: float, alternative: float) -> float:
    """Cambio relativo de ``alternative`` respecto de ``baseline``."""
    base = float(baseline)
    if base == 0.0:
        raise ValueError("La línea base debe ser distinta de cero.")
    return (float(alternative) - base) / base


def mean_or_zero(values: Iterable[float]) -> float:
    """Media aritmética tolerante a una muestra vacía."""
    data = [float(value) for value in values]
    return fsum(data) / len(data) if data else 0.0
