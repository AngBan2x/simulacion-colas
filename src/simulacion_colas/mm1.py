"""Modelo M/M/1 del servidor CI/CD del Problema 1.

Parámetros del enunciado, en minutos:

- llegadas Poisson con ``λ = 0,25`` trabajos por minuto (uno cada 4 minutos);
- servicio exponencial con ``μ = 1/3`` trabajos por minuto (3 minutos);
- un servidor, disciplina FIFO y cola infinita;
- ``ρ = λ/μ = 0,75``, por lo que el sistema es estable.

El módulo incluye las fórmulas analíticas exactas del M/M/1, una replicación
del simulador de eventos discretos y utilidades para resumir varias réplicas
con intervalos de confianza del 95 %.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import nan
from statistics import fmean
from typing import Iterable, Sequence

from .distributions import Exponential, spawn_streams
from .engine import Simulation
from .stats import ConfidenceInterval, TimeWeightedAccumulator, little_ratio, summarize

DEFAULT_ARRIVAL_RATE = 0.25
DEFAULT_SERVICE_RATE = 1.0 / 3.0
DEFAULT_WARMUP = 1_000.0
DEFAULT_HORIZON = 30_000.0
DEFAULT_REPLICATIONS = 50
DEFAULT_BASE_SEED = 1

METRIC_KEYS = ("L", "Lq", "W", "Wq", "utilization")


@dataclass(frozen=True, slots=True)
class MM1Parameters:
    """Parámetros del modelo M/M/1 en minutos."""

    arrival_rate: float = DEFAULT_ARRIVAL_RATE
    service_rate: float = DEFAULT_SERVICE_RATE

    def __post_init__(self) -> None:
        if self.arrival_rate <= 0:
            raise ValueError("La tasa de llegadas debe ser positiva.")
        if self.service_rate <= 0:
            raise ValueError("La tasa de servicio debe ser positiva.")

    @property
    def utilization(self) -> float:
        """Factor de utilización ``ρ``."""
        return self.arrival_rate / self.service_rate

    @property
    def stable(self) -> bool:
        """Indica si se cumple la condición de estabilidad ``ρ < 1``."""
        return self.utilization < 1.0


@dataclass(frozen=True, slots=True)
class MM1Analytical:
    """Resultados analíticos exactos del M/M/1 en estado estacionario."""

    rho: float
    L: float
    Lq: float
    W: float
    Wq: float

    @classmethod
    def from_parameters(cls, parameters: MM1Parameters) -> MM1Analytical:
        if not parameters.stable:
            raise ValueError("El modelo M/M/1 requiere ρ < 1 para tener estado estacionario.")
        rho = parameters.utilization
        return cls(
            rho=rho,
            L=rho / (1.0 - rho),
            Lq=rho * rho / (1.0 - rho),
            W=1.0 / (parameters.service_rate - parameters.arrival_rate),
            Wq=rho / (parameters.service_rate - parameters.arrival_rate),
        )

    @property
    def utilization(self) -> float:
        return self.rho

    def probability_of_n(self, clients: int) -> float:
        """Probabilidad estacionaria de tener ``clients`` trabajos en el sistema."""
        if clients < 0:
            raise ValueError("La cantidad de clientes no puede ser negativa.")
        return (1.0 - self.rho) * self.rho**clients

    def as_dict(self) -> dict[str, float]:
        return {
            "rho": self.rho,
            "L": self.L,
            "Lq": self.Lq,
            "W": self.W,
            "Wq": self.Wq,
        }


@dataclass(frozen=True, slots=True)
class MM1Replication:
    """Resultados de una réplica independiente del simulador M/M/1."""

    seed: int
    warmup: float
    horizon: float
    arrivals: int
    completed: int
    L: float
    Lq: float
    W: float
    Wq: float
    utilization: float

    @property
    def duration(self) -> float:
        return self.horizon - self.warmup

    @property
    def arrival_rate(self) -> float:
        return self.arrivals / self.duration

    @property
    def throughput(self) -> float:
        return self.completed / self.duration

    @property
    def little_l(self) -> float:
        return little_ratio(self.L, self.arrival_rate, self.W)

    @property
    def little_lq(self) -> float:
        return little_ratio(self.Lq, self.arrival_rate, self.Wq)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "seed": self.seed,
            "warmup": self.warmup,
            "horizon": self.horizon,
            "arrivals": self.arrivals,
            "completed": self.completed,
            "L": self.L,
            "Lq": self.Lq,
            "W": self.W,
            "Wq": self.Wq,
            "utilization": self.utilization,
            "little_L": self.little_l,
            "little_Lq": self.little_lq,
        }


class _MM1Run:
    """Ejecución interna de una réplica del M/M/1."""

    def __init__(
        self,
        parameters: MM1Parameters,
        seed: int,
        warmup: float,
        horizon: float,
    ) -> None:
        self.parameters = parameters
        self.seed = seed
        self.warmup = float(warmup)
        self.horizon = float(horizon)

        self.simulation = Simulation()
        streams = spawn_streams(seed, ("llegadas", "servicios"))
        self.arrival_rng = streams["llegadas"]
        self.service_rng = streams["servicios"]
        self.arrival_distribution = Exponential(parameters.arrival_rate)
        self.service_distribution = Exponential(parameters.service_rate)

        self.queue: deque[float] = deque()
        self.busy = False
        self.service_arrival: float | None = None
        self.service_start: float | None = None

        self.system_accumulator: TimeWeightedAccumulator | None = None
        self.queue_accumulator: TimeWeightedAccumulator | None = None
        self.busy_accumulator: TimeWeightedAccumulator | None = None

        self.collecting = True
        self.arrivals = 0
        self.completed = 0
        self.wait_times: list[float] = []
        self.system_times: list[float] = []

    def execute(self) -> MM1Replication:
        self._schedule_arrival()
        self.simulation.run(until=self.horizon)
        self._track(self.horizon)
        self.collecting = False

        duration = self.horizon - self.warmup
        system_area = self.system_accumulator.area() if self.system_accumulator else 0.0
        queue_area = self.queue_accumulator.area() if self.queue_accumulator else 0.0
        busy_area = self.busy_accumulator.area() if self.busy_accumulator else 0.0

        # Drenaje: se completan los trabajos admitidos antes del horizonte para
        # no censurar los tiempos de respuesta de la última parte de la réplica.
        self.simulation.run()

        return MM1Replication(
            seed=self.seed,
            warmup=self.warmup,
            horizon=self.horizon,
            arrivals=self.arrivals,
            completed=self.completed,
            L=system_area / duration,
            Lq=queue_area / duration,
            W=fmean(self.system_times) if self.system_times else nan,
            Wq=fmean(self.wait_times) if self.wait_times else nan,
            utilization=busy_area / duration,
        )

    def _schedule_arrival(self) -> None:
        delay = self.arrival_distribution.sample(self.arrival_rng)
        self.simulation.schedule(delay, self._on_arrival, kind="llegada")

    def _on_arrival(self) -> None:
        now = self.simulation.now
        if now >= self.horizon:
            return

        if self.busy:
            self.queue.append(now)
        else:
            self._start_service(now, now)

        if now >= self.warmup:
            self.arrivals += 1

        self._track(now)
        self._schedule_arrival()

    def _on_departure(self) -> None:
        now = self.simulation.now

        arrival_time = self.service_arrival
        service_start = self.service_start
        self.busy = False
        self.service_arrival = None
        self.service_start = None

        if arrival_time is not None and arrival_time >= self.warmup:
            if service_start is None:
                raise RuntimeError("Un trabajo completado no registra su inicio de servicio.")
            self.wait_times.append(service_start - arrival_time)
            self.system_times.append(now - arrival_time)
            self.completed += 1

        if self.queue:
            next_arrival = self.queue.popleft()
            self._start_service(next_arrival, now)

        self._track(now)

    def _start_service(self, arrival_time: float, start_time: float) -> None:
        self.busy = True
        self.service_arrival = arrival_time
        self.service_start = start_time
        delay = self.service_distribution.sample(self.service_rng)
        self.simulation.schedule(delay, self._on_departure, kind="salida")

    def _current_system(self) -> float:
        return (1.0 if self.busy else 0.0) + len(self.queue)

    def _track(self, time: float) -> None:
        if not self.collecting or time < self.warmup:
            return

        if self.system_accumulator is None:
            start = self.warmup
            self.system_accumulator = TimeWeightedAccumulator(
                start_time=start, initial_value=self._current_system()
            )
            self.queue_accumulator = TimeWeightedAccumulator(
                start_time=start, initial_value=len(self.queue)
            )
            self.busy_accumulator = TimeWeightedAccumulator(
                start_time=start, initial_value=1.0 if self.busy else 0.0
            )
            return

        self.system_accumulator.update(time, self._current_system())
        self.queue_accumulator.update(time, len(self.queue))
        self.busy_accumulator.update(time, 1.0 if self.busy else 0.0)


def simulate_replication(
    parameters: MM1Parameters | None = None,
    *,
    seed: int = DEFAULT_BASE_SEED,
    warmup: float = DEFAULT_WARMUP,
    horizon: float = DEFAULT_HORIZON,
) -> MM1Replication:
    """Ejecuta una réplica del M/M/1 y devuelve sus métricas."""
    params = parameters or MM1Parameters()
    if not params.stable:
        raise ValueError("El modelo M/M/1 requiere ρ < 1 para simularse.")
    if warmup < 0:
        raise ValueError("El warm-up no puede ser negativo.")
    if horizon <= warmup:
        raise ValueError("El horizonte debe ser mayor que el warm-up.")
    return _MM1Run(params, int(seed), warmup, horizon).execute()


def run_replications(
    parameters: MM1Parameters | None = None,
    *,
    replications: int = DEFAULT_REPLICATIONS,
    base_seed: int = DEFAULT_BASE_SEED,
    warmup: float = DEFAULT_WARMUP,
    horizon: float = DEFAULT_HORIZON,
) -> list[MM1Replication]:
    """Ejecuta réplicas independientes con semillas consecutivas."""
    if replications < 2:
        raise ValueError("Se requieren al menos dos réplicas para estimar intervalos.")
    return [
        simulate_replication(
            parameters,
            seed=base_seed + index,
            warmup=warmup,
            horizon=horizon,
        )
        for index in range(replications)
    ]


@dataclass(frozen=True, slots=True)
class MM1MetricSummary:
    """Resumen de una métrica con su valor analítico de referencia."""

    key: str
    confidence_interval: ConfidenceInterval
    analytical: float

    @property
    def contains_analytical(self) -> bool:
        return self.confidence_interval.contains(self.analytical)

    def as_dict(self) -> dict[str, float | int | bool]:
        interval = self.confidence_interval
        return {
            "mean": interval.mean,
            "stdev": interval.stdev,
            "half_width": interval.half_width,
            "lower": interval.lower,
            "upper": interval.upper,
            "relative_error": interval.relative_error,
            "analytical": self.analytical,
            "contains_analytical": self.contains_analytical,
            "n": interval.n,
        }


@dataclass(frozen=True, slots=True)
class MM1Summary:
    """Resumen agregado de una campaña de réplicas del M/M/1."""

    parameters: MM1Parameters
    analytical: MM1Analytical
    replications: int
    base_seed: int
    warmup: float
    horizon: float
    metrics: dict[str, MM1MetricSummary]
    little_L: float
    little_Lq: float

    @property
    def all_intervals_contain_analytical(self) -> bool:
        return all(metric.contains_analytical for metric in self.metrics.values())

    def as_dict(self) -> dict[str, object]:
        return {
            "model": "M/M/1",
            "parameters": {
                "arrival_rate": self.parameters.arrival_rate,
                "service_rate": self.parameters.service_rate,
                "rho": self.parameters.utilization,
                "units": "minutos",
            },
            "design": {
                "replications": self.replications,
                "base_seed": self.base_seed,
                "warmup": self.warmup,
                "horizon": self.horizon,
                "measured_window": self.horizon - self.warmup,
            },
            "analytical": self.analytical.as_dict(),
            "metrics": {key: value.as_dict() for key, value in self.metrics.items()},
            "little": {"L": self.little_L, "Lq": self.little_Lq},
            "all_intervals_contain_analytical": self.all_intervals_contain_analytical,
        }


def summarize_replications(
    replications: Sequence[MM1Replication],
    parameters: MM1Parameters | None = None,
    *,
    confidence: float = 0.95,
) -> MM1Summary:
    """Agrega las réplicas y compara cada IC con el valor analítico exacto."""
    if len(replications) < 2:
        raise ValueError("Se requieren al menos dos réplicas.")

    params = parameters or MM1Parameters()
    analytical = MM1Analytical.from_parameters(params)
    reference = {
        "L": analytical.L,
        "Lq": analytical.Lq,
        "W": analytical.W,
        "Wq": analytical.Wq,
        "utilization": analytical.utilization,
    }

    metrics = {
        key: MM1MetricSummary(
            key=key,
            confidence_interval=summarize(
                (getattr(replication, key) for replication in replications),
                confidence=confidence,
            ),
            analytical=reference[key],
        )
        for key in METRIC_KEYS
    }

    first = replications[0]
    return MM1Summary(
        parameters=params,
        analytical=analytical,
        replications=len(replications),
        base_seed=first.seed,
        warmup=first.warmup,
        horizon=first.horizon,
        metrics=metrics,
        little_L=fmean(replication.little_l for replication in replications),
        little_Lq=fmean(replication.little_lq for replication in replications),
    )


@dataclass(frozen=True, slots=True)
class WarmupPilotRow:
    """Resultado del piloto para un candidato de warm-up."""

    warmup: float
    replications: int
    mean_L: float
    mean_W: float
    mean_Wq: float
    relative_L: float
    relative_W: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "warmup": self.warmup,
            "replications": self.replications,
            "mean_L": self.mean_L,
            "mean_W": self.mean_W,
            "mean_Wq": self.mean_Wq,
            "relative_L": self.relative_L,
            "relative_W": self.relative_W,
        }


def run_warmup_pilot(
    parameters: MM1Parameters | None = None,
    *,
    candidates: Iterable[float] = (0.0, 500.0, 1_000.0, 2_000.0, 5_000.0),
    replications: int = 10,
    base_seed: int = DEFAULT_BASE_SEED,
    horizon: float = DEFAULT_HORIZON,
) -> list[WarmupPilotRow]:
    """Compara el efecto del warm-up sobre las medias de ``L`` y ``W``.

    Cada candidato usa las mismas semillas, de modo que las diferencias se
    atribuyen al descarte del período transitorio y no al azar.
    """
    warmups = sorted(float(value) for value in candidates)
    if not warmups:
        raise ValueError("Se requiere al menos un candidato de warm-up.")
    if any(value < 0 for value in warmups):
        raise ValueError("Los warm-ups no pueden ser negativos.")
    if warmups[-1] >= horizon:
        raise ValueError("Todos los warm-ups deben ser menores que el horizonte.")

    raw: list[tuple[float, float, float, float]] = []
    for warmup in warmups:
        runs = run_replications(
            parameters,
            replications=replications,
            base_seed=base_seed,
            warmup=warmup,
            horizon=horizon,
        )
        raw.append(
            (
                warmup,
                fmean(run.L for run in runs),
                fmean(run.W for run in runs),
                fmean(run.Wq for run in runs),
            )
        )

    reference = raw[-1]
    rows: list[WarmupPilotRow] = []
    for warmup, mean_L, mean_W, mean_Wq in raw:
        rows.append(
            WarmupPilotRow(
                warmup=warmup,
                replications=replications,
                mean_L=mean_L,
                mean_W=mean_W,
                mean_Wq=mean_Wq,
                relative_L=(mean_L - reference[1]) / reference[1],
                relative_W=(mean_W - reference[2]) / reference[2],
            )
        )
    return rows


def recommend_warmup(
    rows: Sequence[WarmupPilotRow],
    *,
    tolerance: float = 0.005,
) -> float:
    """Menor warm-up cuyas medias difieren menos que ``tolerance`` de la cola."""
    if not rows:
        raise ValueError("El piloto no contiene filas.")
    for row in rows:
        if abs(row.relative_L) <= tolerance and abs(row.relative_W) <= tolerance:
            return row.warmup
    return max(row.warmup for row in rows)
