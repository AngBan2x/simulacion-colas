"""Distribuciones de probabilidad reproducibles.

Todas las distribuciones del proyecto expresan sus parámetros en **minutos**.
Cada distribución expone ``sample(rng)`` y no mantiene estado propio: el estado
aleatorio vive en el objeto :class:`random.Random` que recibe la llamada. De
esta forma el resultado es reproducible si se reutiliza la misma semilla.

Convención de nombres:

- ``rate`` (``λ``) es una tasa **por minuto**.
- ``scale`` es la escala de la distribución Weibull, también en minutos.
- ``low`` y ``high`` delimitan el intervalo de una uniforme continua.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gamma
from random import Random
from typing import Protocol, Sequence


class Distribution(Protocol):
    """Contrato mínimo que debe cumplir una distribución del proyecto."""

    def mean(self) -> float:
        """Media teórica de la distribución, en minutos."""

    def sample(self, rng: Random) -> float:
        """Genera una observación usando el generador ``rng``."""


def _require_positive(name: str, value: float) -> float:
    number = float(value)
    if number <= 0:
        raise ValueError(f"{name} debe ser mayor que cero.")
    return number


@dataclass(frozen=True, slots=True)
class Exponential:
    """Distribución exponencial con tasa ``rate`` por minuto."""

    rate: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate", _require_positive("La tasa", self.rate))

    def mean(self) -> float:
        return 1.0 / self.rate

    def sample(self, rng: Random) -> float:
        return rng.expovariate(self.rate)


@dataclass(frozen=True, slots=True)
class Uniform:
    """Distribución uniforme continua en ``[low, high]``."""

    low: float
    high: float

    def __post_init__(self) -> None:
        lower = float(self.low)
        upper = float(self.high)
        if lower < 0:
            raise ValueError("El límite inferior no puede ser negativo.")
        if upper <= lower:
            raise ValueError("El límite superior debe ser mayor que el inferior.")
        object.__setattr__(self, "low", lower)
        object.__setattr__(self, "high", upper)

    def mean(self) -> float:
        return (self.low + self.high) / 2.0

    def sample(self, rng: Random) -> float:
        return rng.uniform(self.low, self.high)


@dataclass(frozen=True, slots=True)
class Weibull:
    """Distribución Weibull con forma ``shape`` y escala ``scale`` en minutos."""

    shape: float
    scale: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape", _require_positive("La forma", self.shape))
        object.__setattr__(self, "scale", _require_positive("La escala", self.scale))

    def mean(self) -> float:
        return self.scale * gamma(1.0 + 1.0 / self.shape)

    def sample(self, rng: Random) -> float:
        return rng.weibullvariate(self.scale, self.shape)


def spawn_streams(seed: int, names: Sequence[str]) -> dict[str, Random]:
    """Crea flujos aleatorios independientes a partir de una semilla maestra.

    La semilla maestra determina de forma determinista la semilla de cada flujo,
    de modo que dos ejecuciones con la misma semilla producen exactamente las
    mismas secuencias. Separar los flujos evita que el orden en que se consumen
    las llegadas altere las secuencias de servicio.
    """
    if not names:
        raise ValueError("Se requiere al menos un nombre de flujo.")
    if len(set(names)) != len(names):
        raise ValueError("Los nombres de los flujos deben ser únicos.")

    master = Random(int(seed))
    return {name: Random(master.getrandbits(64)) for name in names}
