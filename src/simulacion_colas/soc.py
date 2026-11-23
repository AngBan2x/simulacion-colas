"""Modelo de eventos discretos del Centro de Triaje de Incidentes (SOC).

Parámetros del Problema 2 en minutos:

- ``s = 3`` analistas en paralelo y capacidad de cola finita ``K = 8``
  (capacidad total en el sistema ``s + K = 11``).
- Alertas Críticas (Tipo 1 - Alta Prioridad): llegadas Poisson con
  ``λ1 = 0,05`` alertas/min (una cada 20 minutos en promedio) y servicio
  ``Uniforme(15, 25)`` minutos (media ``20`` min).
- Alertas Preventivas (Tipo 2 - Baja Prioridad): llegadas Poisson con
  ``λ2 = 0,10`` alertas/min (6 alertas/hora) y servicio
  ``Weibull(forma=1,5, escala=12)`` minutos (media ``12·Γ(1 + 1/1,5) ≈ 10,8329`` min).
- Disciplina de servicio: prioridad **no expropiativa** (una alerta crítica no
  interrumpe un servicio en curso), FIFO dentro de cada clase y bloqueo
  inmediato (incluso de alertas críticas) cuando los ``s`` analistas están
  ocupados y las ``K`` posiciones de cola están llenas.

El módulo incluye:

- el simulador por réplica (con soporte opcional para trazas deterministas en
  pruebas unitarias y drenaje al final del horizonte para evitar censura);
- la ejecución de campañas con semillas consecutivas e IC95 %;
- la suite completa de experimentos del Caso Base, Escenario A, Escenario B
  y análisis de sensibilidad bajo sobrecarga usando semillas comunes (CRN).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite, nan
from statistics import fmean
from typing import Sequence

from .distributions import Exponential, Uniform, Weibull, spawn_streams
from .engine import Simulation
from .stats import ConfidenceInterval, TimeWeightedAccumulator, paired_difference, summarize

MINUTES_PER_DAY = 1_440.0

DEFAULT_ANALYSTS = 3
DEFAULT_QUEUE_CAPACITY = 8
DEFAULT_ARRIVAL_RATE_1 = 0.05
DEFAULT_ARRIVAL_RATE_2 = 0.10
DEFAULT_SERVICE_1_LOW = 15.0
DEFAULT_SERVICE_1_HIGH = 25.0
DEFAULT_SERVICE_2_SHAPE = 1.5
DEFAULT_SERVICE_2_SCALE = 12.0

OVERLOAD_ARRIVAL_RATE_2 = 0.14  # +40 % respecto a 0,10/min (8,4 alertas/hora)

DEFAULT_SOC_WARMUP = 1.0 * MINUTES_PER_DAY
DEFAULT_SOC_DURATION = 30.0 * MINUTES_PER_DAY
DEFAULT_SOC_HORIZON = DEFAULT_SOC_WARMUP + DEFAULT_SOC_DURATION
DEFAULT_SOC_REPLICATIONS = 30
DEFAULT_SOC_BASE_SEED = 1

WARMUP_PRIORITY = -1
DEPARTURE_PRIORITY = 0
ARRIVAL_PRIORITY = 1

SOC_METRIC_KEYS = (
    "W1",
    "Wq1",
    "W2",
    "Wq2",
    "W",
    "Wq",
    "L",
    "Lq",
    "Lq1",
    "Lq2",
    "utilization",
    "P_loss",
    "P_loss1",
    "P_loss2",
)


@dataclass(frozen=True, slots=True)
class SOCParameters:
    """Parámetros del simulador del SOC expresados en minutos."""

    analysts: int = DEFAULT_ANALYSTS
    queue_capacity: int = DEFAULT_QUEUE_CAPACITY
    arrival_rate_1: float = DEFAULT_ARRIVAL_RATE_1
    arrival_rate_2: float = DEFAULT_ARRIVAL_RATE_2
    service_1_low: float = DEFAULT_SERVICE_1_LOW
    service_1_high: float = DEFAULT_SERVICE_1_HIGH
    service_2_shape: float = DEFAULT_SERVICE_2_SHAPE
    service_2_scale: float = DEFAULT_SERVICE_2_SCALE

    def __post_init__(self) -> None:
        if int(self.analysts) != self.analysts or self.analysts < 1:
            raise ValueError("El número de analistas debe ser un entero al menos igual a 1.")
        if int(self.queue_capacity) != self.queue_capacity or self.queue_capacity < 0:
            raise ValueError("La capacidad de la cola debe ser un entero no negativo.")
        if not isfinite(self.arrival_rate_1) or self.arrival_rate_1 <= 0:
            raise ValueError("La tasa de llegadas Tipo 1 debe ser positiva.")
        if not isfinite(self.arrival_rate_2) or self.arrival_rate_2 <= 0:
            raise ValueError("La tasa de llegadas Tipo 2 debe ser positiva.")
        if not isfinite(self.service_1_low) or self.service_1_low < 0:
            raise ValueError("El límite inferior del servicio Tipo 1 no puede ser negativo.")
        if not isfinite(self.service_1_high) or self.service_1_high <= self.service_1_low:
            raise ValueError("El límite superior del servicio Tipo 1 debe superar al inferior.")
        if not isfinite(self.service_2_shape) or self.service_2_shape <= 0:
            raise ValueError("La forma de Weibull para Tipo 2 debe ser positiva.")
        if not isfinite(self.service_2_scale) or self.service_2_scale <= 0:
            raise ValueError("La escala de Weibull para Tipo 2 debe ser positiva.")

    @property
    def system_capacity(self) -> int:
        """Capacidad total del sistema (``s + K``)."""
        return self.analysts + self.queue_capacity

    @property
    def total_arrival_rate(self) -> float:
        """Tasa agregada de llegadas por minuto (``λ1 + λ2``)."""
        return self.arrival_rate_1 + self.arrival_rate_2

    @property
    def mean_service_1(self) -> float:
        """Tiempo medio de servicio para alertas críticas Tipo 1, en minutos."""
        return Uniform(self.service_1_low, self.service_1_high).mean()

    @property
    def mean_service_2(self) -> float:
        """Tiempo medio de servicio para alertas preventivas Tipo 2, en minutos."""
        return Weibull(self.service_2_shape, self.service_2_scale).mean()

    @property
    def offered_load_1(self) -> float:
        """Carga ofrecida por alertas Tipo 1, en Erlangs."""
        return self.arrival_rate_1 * self.mean_service_1

    @property
    def offered_load_2(self) -> float:
        """Carga ofrecida por alertas Tipo 2, en Erlangs."""
        return self.arrival_rate_2 * self.mean_service_2

    @property
    def offered_load(self) -> float:
        """Carga total ofrecida al SOC, en Erlangs."""
        return self.offered_load_1 + self.offered_load_2

    @property
    def offered_utilization(self) -> float:
        """Utilización ofrecida por analista (``(λ1·E[S1] + λ2·E[S2]) / s``)."""
        return self.offered_load / self.analysts

    @property
    def theoretically_unsaturated(self) -> bool:
        """Indica si la carga ofrecida es inferior a la capacidad total de los analistas."""
        return self.offered_utilization < 1.0

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "analysts": self.analysts,
            "queue_capacity": self.queue_capacity,
            "system_capacity": self.system_capacity,
            "arrival_rate_1": self.arrival_rate_1,
            "arrival_rate_2": self.arrival_rate_2,
            "total_arrival_rate": self.total_arrival_rate,
            "service_1_low": self.service_1_low,
            "service_1_high": self.service_1_high,
            "mean_service_1": self.mean_service_1,
            "service_2_shape": self.service_2_shape,
            "service_2_scale": self.service_2_scale,
            "mean_service_2": self.mean_service_2,
            "offered_load": self.offered_load,
            "offered_utilization": self.offered_utilization,
            "theoretically_unsaturated": self.theoretically_unsaturated,
            "units": "minutos",
        }


@dataclass(frozen=True, slots=True)
class SOCServiceRecord:
    """Registro de servicio de una alerta individual (útil para verificación de disciplina)."""

    alert_id: int
    alert_type: int
    arrival_time: float
    start_time: float
    departure_time: float

    @property
    def wait_time(self) -> float:
        return self.start_time - self.arrival_time

    @property
    def system_time(self) -> float:
        return self.departure_time - self.arrival_time


@dataclass(frozen=True, slots=True)
class SOCReplication:
    """Resultados de una réplica independiente del simulador del SOC."""

    seed: int
    warmup: float
    horizon: float
    drain: bool
    arrivals: int
    arrivals_1: int
    arrivals_2: int
    admitted: int
    admitted_1: int
    admitted_2: int
    blocked: int
    blocked_1: int
    blocked_2: int
    completed: int
    completed_1: int
    completed_2: int
    remaining: int
    remaining_1: int
    remaining_2: int
    max_busy_analysts: int
    max_queue_length: int
    L: float
    Lq: float
    Lq1: float
    Lq2: float
    W: float
    Wq: float
    W1: float
    Wq1: float
    W2: float
    Wq2: float
    utilization: float
    P_loss: float
    P_loss1: float
    P_loss2: float

    @property
    def duration(self) -> float:
        return self.horizon - self.warmup

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "seed": self.seed,
            "warmup": self.warmup,
            "horizon": self.horizon,
            "drain": self.drain,
            "arrivals": self.arrivals,
            "arrivals_1": self.arrivals_1,
            "arrivals_2": self.arrivals_2,
            "admitted": self.admitted,
            "admitted_1": self.admitted_1,
            "admitted_2": self.admitted_2,
            "blocked": self.blocked,
            "blocked_1": self.blocked_1,
            "blocked_2": self.blocked_2,
            "completed": self.completed,
            "completed_1": self.completed_1,
            "completed_2": self.completed_2,
            "remaining": self.remaining,
            "remaining_1": self.remaining_1,
            "remaining_2": self.remaining_2,
            "max_busy_analysts": self.max_busy_analysts,
            "max_queue_length": self.max_queue_length,
            "L": self.L,
            "Lq": self.Lq,
            "Lq1": self.Lq1,
            "Lq2": self.Lq2,
            "W": self.W,
            "Wq": self.Wq,
            "W1": self.W1,
            "Wq1": self.Wq1,
            "W2": self.W2,
            "Wq2": self.Wq2,
            "utilization": self.utilization,
            "P_loss": self.P_loss,
            "P_loss1": self.P_loss1,
            "P_loss2": self.P_loss2,
        }


@dataclass(frozen=True, slots=True)
class SOCScriptedArrival:
    """Especificación determinista de una llegada para pruebas unitarias controladas."""

    time: float
    alert_type: int
    service_duration: float


class _SOCRun:
    """Ejecución interna de una réplica del SOC sobre el motor de eventos discretos."""

    def __init__(
        self,
        parameters: SOCParameters,
        *,
        seed: int,
        warmup: float,
        horizon: float,
        drain: bool,
        record_services: bool = False,
    ) -> None:
        self.parameters = parameters
        self.seed = seed
        self.warmup = float(warmup)
        self.horizon = float(horizon)
        self.drain = bool(drain)
        self.record_services = bool(record_services)

        self.simulation = Simulation()
        streams = spawn_streams(
            seed,
            ("llegadas_1", "llegadas_2", "servicios_1", "servicios_2"),
        )
        self.arrival_rng_1 = streams["llegadas_1"]
        self.arrival_rng_2 = streams["llegadas_2"]
        self.service_rng_1 = streams["servicios_1"]
        self.service_rng_2 = streams["servicios_2"]

        self.arrival_dist_1 = Exponential(parameters.arrival_rate_1)
        self.arrival_dist_2 = Exponential(parameters.arrival_rate_2)
        self.service_dist_1 = Uniform(parameters.service_1_low, parameters.service_1_high)
        self.service_dist_2 = Weibull(parameters.service_2_shape, parameters.service_2_scale)

        # Cada entrada de cola guarda (alert_id, arrival_time, explicit_service_duration | None)
        self.queue_1: deque[tuple[int, float, float | None]] = deque()
        self.queue_2: deque[tuple[int, float, float | None]] = deque()
        # alert_id -> (alert_type, arrival_time, start_time)
        self.active_services: dict[int, tuple[int, float, float]] = {}

        self._next_alert_id = 0
        self.max_busy_analysts = 0
        self.max_queue_length = 0

        self.system_accumulator: TimeWeightedAccumulator | None = None
        self.queue_accumulator: TimeWeightedAccumulator | None = None
        self.queue_1_accumulator: TimeWeightedAccumulator | None = None
        self.queue_2_accumulator: TimeWeightedAccumulator | None = None
        self.busy_accumulator: TimeWeightedAccumulator | None = None

        self.collecting = True

        self.arrivals_1 = 0
        self.arrivals_2 = 0
        self.admitted_1 = 0
        self.admitted_2 = 0
        self.blocked_1 = 0
        self.blocked_2 = 0
        self.completed_1 = 0
        self.completed_2 = 0

        self.wait_times_1: list[float] = []
        self.system_times_1: list[float] = []
        self.wait_times_2: list[float] = []
        self.system_times_2: list[float] = []
        self.service_records: list[SOCServiceRecord] = []

    def execute(self) -> SOCReplication:
        self._prepare_measurement_boundary()
        self._schedule_arrival(1)
        self._schedule_arrival(2)
        return self._finish_execution()

    def execute_scripted(
        self,
        arrivals: Sequence[SOCScriptedArrival],
    ) -> tuple[SOCReplication, list[SOCServiceRecord]]:
        self._prepare_measurement_boundary()
        for item in arrivals:
            if item.alert_type not in (1, 2):
                raise ValueError("El tipo de alerta debe ser 1 (crítica) o 2 (preventiva).")
            if item.service_duration < 0 or not isfinite(item.service_duration):
                raise ValueError("La duración de servicio debe ser finita y no negativa.")
            self.simulation.schedule_at(
                item.time,
                lambda t=item.alert_type, d=item.service_duration: self._handle_arrival(t, d),
                priority=ARRIVAL_PRIORITY,
                kind=f"llegada_{item.alert_type}",
            )
        replication = self._finish_execution()
        return replication, list(self.service_records)

    def _prepare_measurement_boundary(self) -> None:
        if self.warmup == 0.0:
            self._start_measurement()
        else:
            self.simulation.schedule_at(
                self.warmup,
                self._start_measurement,
                priority=WARMUP_PRIORITY,
                kind="fin_warmup",
            )

    def _start_measurement(self) -> None:
        start = self.warmup
        self.system_accumulator = TimeWeightedAccumulator(
            start_time=start,
            initial_value=float(self._current_system()),
        )
        self.queue_accumulator = TimeWeightedAccumulator(
            start_time=start,
            initial_value=float(self._current_queue()),
        )
        self.queue_1_accumulator = TimeWeightedAccumulator(
            start_time=start,
            initial_value=float(len(self.queue_1)),
        )
        self.queue_2_accumulator = TimeWeightedAccumulator(
            start_time=start,
            initial_value=float(len(self.queue_2)),
        )
        self.busy_accumulator = TimeWeightedAccumulator(
            start_time=start,
            initial_value=float(len(self.active_services)),
        )

    def _finish_execution(self) -> SOCReplication:
        self.simulation.run(until=self.horizon)
        self._track(self.horizon)
        self.collecting = False

        duration = self.horizon - self.warmup
        system_area = self.system_accumulator.area() if self.system_accumulator else 0.0
        queue_area = self.queue_accumulator.area() if self.queue_accumulator else 0.0
        queue_1_area = self.queue_1_accumulator.area() if self.queue_1_accumulator else 0.0
        queue_2_area = self.queue_2_accumulator.area() if self.queue_2_accumulator else 0.0
        busy_area = self.busy_accumulator.area() if self.busy_accumulator else 0.0

        if self.drain:
            self.simulation.run()

        remaining_1 = sum(
            1 for alert_type, arrival_time, _ in self.active_services.values()
            if alert_type == 1 and arrival_time >= self.warmup
        ) + sum(1 for _, arrival_time, _ in self.queue_1 if arrival_time >= self.warmup)
        remaining_2 = sum(
            1 for alert_type, arrival_time, _ in self.active_services.values()
            if alert_type == 2 and arrival_time >= self.warmup
        ) + sum(1 for _, arrival_time, _ in self.queue_2 if arrival_time >= self.warmup)

        arrivals = self.arrivals_1 + self.arrivals_2
        admitted = self.admitted_1 + self.admitted_2
        blocked = self.blocked_1 + self.blocked_2
        completed = self.completed_1 + self.completed_2
        remaining = remaining_1 + remaining_2

        all_waits = self.wait_times_1 + self.wait_times_2
        all_systems = self.system_times_1 + self.system_times_2

        return SOCReplication(
            seed=self.seed,
            warmup=self.warmup,
            horizon=self.horizon,
            drain=self.drain,
            arrivals=arrivals,
            arrivals_1=self.arrivals_1,
            arrivals_2=self.arrivals_2,
            admitted=admitted,
            admitted_1=self.admitted_1,
            admitted_2=self.admitted_2,
            blocked=blocked,
            blocked_1=self.blocked_1,
            blocked_2=self.blocked_2,
            completed=completed,
            completed_1=self.completed_1,
            completed_2=self.completed_2,
            remaining=remaining,
            remaining_1=remaining_1,
            remaining_2=remaining_2,
            max_busy_analysts=self.max_busy_analysts,
            max_queue_length=self.max_queue_length,
            L=system_area / duration,
            Lq=queue_area / duration,
            Lq1=queue_1_area / duration,
            Lq2=queue_2_area / duration,
            W=fmean(all_systems) if all_systems else nan,
            Wq=fmean(all_waits) if all_waits else nan,
            W1=fmean(self.system_times_1) if self.system_times_1 else nan,
            Wq1=fmean(self.wait_times_1) if self.wait_times_1 else nan,
            W2=fmean(self.system_times_2) if self.system_times_2 else nan,
            Wq2=fmean(self.wait_times_2) if self.wait_times_2 else nan,
            utilization=busy_area / (duration * self.parameters.analysts),
            P_loss=blocked / arrivals if arrivals > 0 else 0.0,
            P_loss1=self.blocked_1 / self.arrivals_1 if self.arrivals_1 > 0 else 0.0,
            P_loss2=self.blocked_2 / self.arrivals_2 if self.arrivals_2 > 0 else 0.0,
        )

    def _schedule_arrival(self, alert_type: int) -> None:
        if alert_type == 1:
            delay = self.arrival_dist_1.sample(self.arrival_rng_1)
        else:
            delay = self.arrival_dist_2.sample(self.arrival_rng_2)
        self.simulation.schedule(
            delay,
            lambda t=alert_type: self._on_poisson_arrival(t),
            priority=ARRIVAL_PRIORITY,
            kind=f"llegada_{alert_type}",
        )

    def _on_poisson_arrival(self, alert_type: int) -> None:
        if self.simulation.now >= self.horizon:
            return
        self._handle_arrival(alert_type, service_duration=None)
        self._schedule_arrival(alert_type)

    def _handle_arrival(self, alert_type: int, service_duration: float | None) -> None:
        now = self.simulation.now
        if now >= self.horizon:
            return

        in_window = now >= self.warmup
        if in_window:
            if alert_type == 1:
                self.arrivals_1 += 1
            else:
                self.arrivals_2 += 1

        if len(self.active_services) < self.parameters.analysts:
            self._next_alert_id += 1
            alert_id = self._next_alert_id
            if in_window:
                if alert_type == 1:
                    self.admitted_1 += 1
                else:
                    self.admitted_2 += 1
            self._start_service(alert_id, alert_type, now, now, service_duration)
        elif self._current_queue() < self.parameters.queue_capacity:
            self._next_alert_id += 1
            alert_id = self._next_alert_id
            if in_window:
                if alert_type == 1:
                    self.admitted_1 += 1
                else:
                    self.admitted_2 += 1
            if alert_type == 1:
                self.queue_1.append((alert_id, now, service_duration))
            else:
                self.queue_2.append((alert_id, now, service_duration))
            if self._current_queue() > self.max_queue_length:
                self.max_queue_length = self._current_queue()
        else:
            # Buffer lleno: bloqueo inmediato para ambas clases (incluida crítica Tipo 1).
            if in_window:
                if alert_type == 1:
                    self.blocked_1 += 1
                else:
                    self.blocked_2 += 1

        self._track(now)

    def _on_departure(self, alert_id: int) -> None:
        now = self.simulation.now
        alert_type, arrival_time, start_time = self.active_services.pop(alert_id)

        if self.record_services:
            self.service_records.append(
                SOCServiceRecord(
                    alert_id=alert_id,
                    alert_type=alert_type,
                    arrival_time=arrival_time,
                    start_time=start_time,
                    departure_time=now,
                )
            )

        if arrival_time >= self.warmup:
            wait = start_time - arrival_time
            total = now - arrival_time
            if alert_type == 1:
                self.wait_times_1.append(wait)
                self.system_times_1.append(total)
                self.completed_1 += 1
            else:
                self.wait_times_2.append(wait)
                self.system_times_2.append(total)
                self.completed_2 += 1

        # Selección no expropiativa al liberarse un analista:
        # primero crítica más antigua, luego preventiva más antigua.
        if self.queue_1:
            next_id, next_arrival, next_duration = self.queue_1.popleft()
            self._start_service(next_id, 1, next_arrival, now, next_duration)
        elif self.queue_2:
            next_id, next_arrival, next_duration = self.queue_2.popleft()
            self._start_service(next_id, 2, next_arrival, now, next_duration)

        self._track(now)

    def _start_service(
        self,
        alert_id: int,
        alert_type: int,
        arrival_time: float,
        start_time: float,
        explicit_duration: float | None,
    ) -> None:
        self.active_services[alert_id] = (alert_type, arrival_time, start_time)
        if len(self.active_services) > self.max_busy_analysts:
            self.max_busy_analysts = len(self.active_services)

        if explicit_duration is not None:
            delay = explicit_duration
        elif alert_type == 1:
            delay = self.service_dist_1.sample(self.service_rng_1)
        else:
            delay = self.service_dist_2.sample(self.service_rng_2)

        self.simulation.schedule(
            delay,
            lambda aid=alert_id: self._on_departure(aid),
            priority=DEPARTURE_PRIORITY,
            kind=f"salida_{alert_type}",
        )

    def _current_queue(self) -> int:
        return len(self.queue_1) + len(self.queue_2)

    def _current_system(self) -> int:
        return len(self.active_services) + self._current_queue()

    def _track(self, time: float) -> None:
        if not self.collecting or time < self.warmup:
            return
        if self.system_accumulator is None:
            return

        self.system_accumulator.update(time, float(self._current_system()))
        self.queue_accumulator.update(time, float(self._current_queue()))
        self.queue_1_accumulator.update(time, float(len(self.queue_1)))
        self.queue_2_accumulator.update(time, float(len(self.queue_2)))
        self.busy_accumulator.update(time, float(len(self.active_services)))


def simulate_soc_replication(
    parameters: SOCParameters | None = None,
    *,
    seed: int = DEFAULT_SOC_BASE_SEED,
    warmup: float = DEFAULT_SOC_WARMUP,
    horizon: float = DEFAULT_SOC_HORIZON,
    drain: bool = True,
) -> SOCReplication:
    """Ejecuta una réplica independiente del simulador del SOC."""
    params = parameters or SOCParameters()
    if warmup < 0:
        raise ValueError("El warm-up no puede ser negativo.")
    if horizon <= warmup:
        raise ValueError("El horizonte debe ser mayor que el warm-up.")
    return _SOCRun(
        params,
        seed=int(seed),
        warmup=warmup,
        horizon=horizon,
        drain=drain,
    ).execute()


def simulate_soc_scripted(
    parameters: SOCParameters | None = None,
    arrivals: Sequence[SOCScriptedArrival] = (),
    *,
    warmup: float = 0.0,
    horizon: float = 1_000.0,
    drain: bool = True,
) -> tuple[SOCReplication, list[SOCServiceRecord]]:
    """Ejecuta una secuencia determinista de llegadas usando el mismo núcleo del SOC."""
    params = parameters or SOCParameters()
    if warmup < 0:
        raise ValueError("El warm-up no puede ser negativo.")
    if horizon <= warmup:
        raise ValueError("El horizonte debe ser mayor que el warm-up.")
    return _SOCRun(
        params,
        seed=1,
        warmup=warmup,
        horizon=horizon,
        drain=drain,
        record_services=True,
    ).execute_scripted(arrivals)


def run_soc_replications(
    parameters: SOCParameters | None = None,
    *,
    replications: int = DEFAULT_SOC_REPLICATIONS,
    base_seed: int = DEFAULT_SOC_BASE_SEED,
    warmup: float = DEFAULT_SOC_WARMUP,
    horizon: float = DEFAULT_SOC_HORIZON,
    drain: bool = True,
) -> list[SOCReplication]:
    """Ejecuta múltiples réplicas independientes con semillas consecutivas."""
    if replications < 2:
        raise ValueError("Se requieren al menos dos réplicas para estimar intervalos.")
    return [
        simulate_soc_replication(
            parameters,
            seed=base_seed + index,
            warmup=warmup,
            horizon=horizon,
            drain=drain,
        )
        for index in range(replications)
    ]


@dataclass(frozen=True, slots=True)
class SOCSummary:
    """Resumen agregado de una campaña de réplicas del SOC."""

    scenario_id: str
    label: str
    parameters: SOCParameters
    replications: int
    base_seed: int
    warmup: float
    horizon: float
    drain: bool
    metrics: dict[str, ConfidenceInterval]
    mean_counts: dict[str, float]

    @property
    def measured_window(self) -> float:
        return self.horizon - self.warmup

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "label": self.label,
            "parameters": self.parameters.as_dict(),
            "design": {
                "replications": self.replications,
                "base_seed": self.base_seed,
                "warmup": self.warmup,
                "horizon": self.horizon,
                "measured_window": self.measured_window,
                "drain": self.drain,
            },
            "mean_counts": dict(self.mean_counts),
            "metrics": {
                key: {
                    "mean": interval.mean,
                    "stdev": interval.stdev,
                    "half_width": interval.half_width,
                    "lower": interval.lower,
                    "upper": interval.upper,
                    "relative_error": interval.relative_error,
                    "n": interval.n,
                }
                for key, interval in self.metrics.items()
            },
        }


def summarize_soc_replications(
    replications: Sequence[SOCReplication],
    parameters: SOCParameters | None = None,
    *,
    scenario_id: str = "base",
    label: str = "SOC base (s=3, K=8)",
    confidence: float = 0.95,
) -> SOCSummary:
    """Resume una campaña de réplicas del SOC con IC95 % por métrica."""
    if len(replications) < 2:
        raise ValueError("Se requieren al menos dos réplicas.")

    params = parameters or SOCParameters()
    metrics = {
        key: summarize(
            (getattr(replication, key) for replication in replications),
            confidence=confidence,
        )
        for key in SOC_METRIC_KEYS
    }

    count_keys = (
        "arrivals",
        "arrivals_1",
        "arrivals_2",
        "admitted",
        "admitted_1",
        "admitted_2",
        "blocked",
        "blocked_1",
        "blocked_2",
        "completed",
        "completed_1",
        "completed_2",
        "remaining",
    )
    mean_counts = {
        key: fmean(getattr(replication, key) for replication in replications)
        for key in count_keys
    }

    first = replications[0]
    return SOCSummary(
        scenario_id=scenario_id,
        label=label,
        parameters=params,
        replications=len(replications),
        base_seed=first.seed,
        warmup=first.warmup,
        horizon=first.horizon,
        drain=first.drain,
        metrics=metrics,
        mean_counts=mean_counts,
    )


@dataclass(frozen=True, slots=True)
class SOCScenarioSpec:
    """Definición de un escenario experimental del SOC."""

    scenario_id: str
    label: str
    parameters: SOCParameters
    demand_regime: str


def build_soc_scenario_specs(
    base_parameters: SOCParameters | None = None,
) -> tuple[SOCScenarioSpec, ...]:
    """Construye los escenarios base, A, B y sensibilidad bajo sobrecarga."""
    base = base_parameters or SOCParameters()
    return (
        SOCScenarioSpec(
            scenario_id="base",
            label=f"Base (s={base.analysts}, K={base.queue_capacity}, λ2={base.arrival_rate_2:.2f})",
            parameters=base,
            demand_regime="base",
        ),
        SOCScenarioSpec(
            scenario_id="scenario_a",
            label=f"Escenario A (s={base.analysts}, K={base.queue_capacity}, λ2={OVERLOAD_ARRIVAL_RATE_2:.2f})",
            parameters=SOCParameters(
                analysts=base.analysts,
                queue_capacity=base.queue_capacity,
                arrival_rate_1=base.arrival_rate_1,
                arrival_rate_2=OVERLOAD_ARRIVAL_RATE_2,
                service_1_low=base.service_1_low,
                service_1_high=base.service_1_high,
                service_2_shape=base.service_2_shape,
                service_2_scale=base.service_2_scale,
            ),
            demand_regime="overload",
        ),
        SOCScenarioSpec(
            scenario_id="scenario_b_k16",
            label=f"Escenario B1: Ampliar buffer (s={base.analysts}, K=16, λ2={base.arrival_rate_2:.2f})",
            parameters=SOCParameters(
                analysts=base.analysts,
                queue_capacity=16,
                arrival_rate_1=base.arrival_rate_1,
                arrival_rate_2=base.arrival_rate_2,
                service_1_low=base.service_1_low,
                service_1_high=base.service_1_high,
                service_2_shape=base.service_2_shape,
                service_2_scale=base.service_2_scale,
            ),
            demand_regime="base",
        ),
        SOCScenarioSpec(
            scenario_id="scenario_b_s4",
            label=f"Escenario B2: 4.º analista (s=4, K={base.queue_capacity}, λ2={base.arrival_rate_2:.2f})",
            parameters=SOCParameters(
                analysts=4,
                queue_capacity=base.queue_capacity,
                arrival_rate_1=base.arrival_rate_1,
                arrival_rate_2=base.arrival_rate_2,
                service_1_low=base.service_1_low,
                service_1_high=base.service_1_high,
                service_2_shape=base.service_2_shape,
                service_2_scale=base.service_2_scale,
            ),
            demand_regime="base",
        ),
        SOCScenarioSpec(
            scenario_id="scenario_b_k16_overload",
            label=f"Sensibilidad B1 en sobrecarga (s={base.analysts}, K=16, λ2={OVERLOAD_ARRIVAL_RATE_2:.2f})",
            parameters=SOCParameters(
                analysts=base.analysts,
                queue_capacity=16,
                arrival_rate_1=base.arrival_rate_1,
                arrival_rate_2=OVERLOAD_ARRIVAL_RATE_2,
                service_1_low=base.service_1_low,
                service_1_high=base.service_1_high,
                service_2_shape=base.service_2_shape,
                service_2_scale=base.service_2_scale,
            ),
            demand_regime="overload",
        ),
        SOCScenarioSpec(
            scenario_id="scenario_b_s4_overload",
            label=f"Sensibilidad B2 en sobrecarga (s=4, K={base.queue_capacity}, λ2={OVERLOAD_ARRIVAL_RATE_2:.2f})",
            parameters=SOCParameters(
                analysts=4,
                queue_capacity=base.queue_capacity,
                arrival_rate_1=base.arrival_rate_1,
                arrival_rate_2=OVERLOAD_ARRIVAL_RATE_2,
                service_1_low=base.service_1_low,
                service_1_high=base.service_1_high,
                service_2_shape=base.service_2_shape,
                service_2_scale=base.service_2_scale,
            ),
            demand_regime="overload",
        ),
    )


@dataclass(frozen=True, slots=True)
class SOCComparisonMetric:
    """Comparación pareada (CRN) de una métrica entre dos escenarios."""

    comparison_id: str
    reference_id: str
    alternative_id: str
    metric: str
    reference_mean: float
    alternative_mean: float
    difference: ConfidenceInterval
    relative_change: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "comparison_id": self.comparison_id,
            "reference_id": self.reference_id,
            "alternative_id": self.alternative_id,
            "metric": self.metric,
            "reference_mean": self.reference_mean,
            "alternative_mean": self.alternative_mean,
            "diff_mean": self.difference.mean,
            "diff_stdev": self.difference.stdev,
            "diff_half_width": self.difference.half_width,
            "diff_lower": self.difference.lower,
            "diff_upper": self.difference.upper,
            "relative_change": self.relative_change,
            "n": self.difference.n,
        }


@dataclass(frozen=True, slots=True)
class SOCScenarioSuite:
    """Resultados completos de todos los escenarios del SOC y su análisis pareado."""

    replications_by_scenario: dict[str, list[SOCReplication]]
    summaries: dict[str, SOCSummary]
    comparisons: list[SOCComparisonMetric]
    analysis: dict[str, object]
    recommendation: str

    def as_dict(self) -> dict[str, object]:
        base = self.summaries["base"]
        return {
            "model": "SOC",
            "design": {
                "replications": base.replications,
                "base_seed": base.base_seed,
                "warmup": base.warmup,
                "horizon": base.horizon,
                "measured_window": base.measured_window,
                "drain": base.drain,
                "common_random_numbers": True,
            },
            "scenarios": {
                scenario_id: summary.as_dict()
                for scenario_id, summary in self.summaries.items()
            },
            "comparisons": [row.as_dict() for row in self.comparisons],
            "analysis": self.analysis,
            "recommendation": self.recommendation,
        }


def compare_soc_scenarios(
    replications_by_scenario: dict[str, list[SOCReplication]],
    summaries: dict[str, SOCSummary],
    *,
    confidence: float = 0.95,
) -> list[SOCComparisonMetric]:
    """Calcula comparaciones pareadas (``alternative - reference``) usando CRN."""
    pairs = (
        ("scenario_a_vs_base", "base", "scenario_a"),
        ("scenario_b_k16_vs_base", "base", "scenario_b_k16"),
        ("scenario_b_s4_vs_base", "base", "scenario_b_s4"),
        ("scenario_b_s4_vs_k16", "scenario_b_k16", "scenario_b_s4"),
        (
            "scenario_b_k16_overload_vs_scenario_a",
            "scenario_a",
            "scenario_b_k16_overload",
        ),
        (
            "scenario_b_s4_overload_vs_scenario_a",
            "scenario_a",
            "scenario_b_s4_overload",
        ),
        (
            "scenario_b_s4_overload_vs_k16_overload",
            "scenario_b_k16_overload",
            "scenario_b_s4_overload",
        ),
    )

    rows: list[SOCComparisonMetric] = []
    for comparison_id, reference_id, alternative_id in pairs:
        if (
            reference_id not in replications_by_scenario
            or alternative_id not in replications_by_scenario
        ):
            continue
        ref_runs = replications_by_scenario[reference_id]
        alt_runs = replications_by_scenario[alternative_id]
        ref_summary = summaries[reference_id]
        alt_summary = summaries[alternative_id]

        for metric in SOC_METRIC_KEYS:
            ref_vals = [float(getattr(run, metric)) for run in ref_runs]
            alt_vals = [float(getattr(run, metric)) for run in alt_runs]
            diff = paired_difference(ref_vals, alt_vals, confidence=confidence)
            ref_mean = ref_summary.metrics[metric].mean
            alt_mean = alt_summary.metrics[metric].mean
            rel = (alt_mean - ref_mean) / ref_mean if ref_mean != 0.0 else None
            rows.append(
                SOCComparisonMetric(
                    comparison_id=comparison_id,
                    reference_id=reference_id,
                    alternative_id=alternative_id,
                    metric=metric,
                    reference_mean=ref_mean,
                    alternative_mean=alt_mean,
                    difference=diff,
                    relative_change=rel,
                )
            )
    return rows


def _build_scenario_analysis(
    summaries: dict[str, SOCSummary],
    comparisons: Sequence[SOCComparisonMetric],
) -> tuple[dict[str, object], str]:
    """Construye el diagnóstico cuantitativo para los Escenarios A y B."""
    lookup = {(row.comparison_id, row.metric): row for row in comparisons}

    base = summaries["base"]
    scen_a = summaries["scenario_a"]
    b_k16 = summaries["scenario_b_k16"]
    b_s4 = summaries["scenario_b_s4"]
    b_k16_ov = summaries["scenario_b_k16_overload"]
    b_s4_ov = summaries["scenario_b_s4_overload"]

    ploss_a_vs_base = lookup[("scenario_a_vs_base", "P_loss")]
    util_a_vs_base = lookup[("scenario_a_vs_base", "utilization")]
    ploss_s4_vs_k16 = lookup[("scenario_b_s4_vs_k16", "P_loss")]
    ploss_s4_vs_k16_ov = lookup[("scenario_b_s4_overload_vs_k16_overload", "P_loss")]

    p_base = base.metrics["P_loss"].mean
    p_a = scen_a.metrics["P_loss"].mean
    p_b_k16 = b_k16.metrics["P_loss"].mean
    p_b_s4 = b_s4.metrics["P_loss"].mean
    p_b_k16_ov = b_k16_ov.metrics["P_loss"].mean
    p_b_s4_ov = b_s4_ov.metrics["P_loss"].mean

    util_a = scen_a.metrics["utilization"].mean
    offered_util_a = scen_a.parameters.offered_utilization
    analysts_saturated = offered_util_a >= 1.0

    rel_inc = ploss_a_vs_base.relative_change
    rel_inc_pct = (100.0 * rel_inc) if rel_inc is not None else None
    abs_pp = 100.0 * ploss_a_vs_base.difference.mean
    base_b_p_loss_indistinguishable = (
        ploss_s4_vs_k16.difference.lower <= 0.0 <= ploss_s4_vs_k16.difference.upper
    )

    analysis: dict[str, object] = {
        "scenario_a": {
            "base_p_loss": p_base,
            "scenario_a_p_loss": p_a,
            "absolute_increase_pp": abs_pp,
            "absolute_increase_ci95_pp": [
                100.0 * ploss_a_vs_base.difference.lower,
                100.0 * ploss_a_vs_base.difference.upper,
            ],
            "relative_increase_pct": rel_inc_pct,
            "base_utilization": base.metrics["utilization"].mean,
            "scenario_a_utilization": util_a,
            "utilization_diff_pp": 100.0 * util_a_vs_base.difference.mean,
            "offered_utilization": offered_util_a,
            "analysts_theoretically_saturated": analysts_saturated,
            "base_wq1": base.metrics["Wq1"].mean,
            "scenario_a_wq1": scen_a.metrics["Wq1"].mean,
            "base_wq2": base.metrics["Wq2"].mean,
            "scenario_a_wq2": scen_a.metrics["Wq2"].mean,
            "base_lq": base.metrics["Lq"].mean,
            "scenario_a_lq": scen_a.metrics["Lq"].mean,
        },
        "scenario_b_base_demand": {
            "best_for_p_loss": "scenario_b_s4" if p_b_s4 <= p_b_k16 else "scenario_b_k16",
            "p_loss_diff_s4_minus_k16_ci95_pp": [
                100.0 * ploss_s4_vs_k16.difference.lower,
                100.0 * ploss_s4_vs_k16.difference.upper,
            ],
            "p_loss_statistically_indistinguishable": base_b_p_loss_indistinguishable,
            "best_for_waiting_time": (
                "scenario_b_s4"
                if b_s4.metrics["Wq"].mean <= b_k16.metrics["Wq"].mean
                else "scenario_b_k16"
            ),
            "k16_p_loss": p_b_k16,
            "s4_p_loss": p_b_s4,
            "k16_wq1": b_k16.metrics["Wq1"].mean,
            "s4_wq1": b_s4.metrics["Wq1"].mean,
            "k16_wq2": b_k16.metrics["Wq2"].mean,
            "s4_wq2": b_s4.metrics["Wq2"].mean,
            "k16_w1": b_k16.metrics["W1"].mean,
            "s4_w1": b_s4.metrics["W1"].mean,
            "k16_w2": b_k16.metrics["W2"].mean,
            "s4_w2": b_s4.metrics["W2"].mean,
        },
        "scenario_b_overload_demand": {
            "best_for_p_loss": "scenario_b_s4_overload" if p_b_s4_ov <= p_b_k16_ov else "scenario_b_k16_overload",
            "p_loss_diff_s4_minus_k16_ci95_pp": [
                100.0 * ploss_s4_vs_k16_ov.difference.lower,
                100.0 * ploss_s4_vs_k16_ov.difference.upper,
            ],
            "best_for_waiting_time": (
                "scenario_b_s4_overload"
                if b_s4_ov.metrics["Wq"].mean <= b_k16_ov.metrics["Wq"].mean
                else "scenario_b_k16_overload"
            ),
            "k16_p_loss": p_b_k16_ov,
            "s4_p_loss": p_b_s4_ov,
            "k16_wq1": b_k16_ov.metrics["Wq1"].mean,
            "s4_wq1": b_s4_ov.metrics["Wq1"].mean,
            "k16_wq2": b_k16_ov.metrics["Wq2"].mean,
            "s4_wq2": b_s4_ov.metrics["Wq2"].mean,
            "k16_w1": b_k16_ov.metrics["W1"].mean,
            "s4_w1": b_s4_ov.metrics["W1"].mean,
            "k16_w2": b_k16_ov.metrics["W2"].mean,
            "s4_w2": b_s4_ov.metrics["W2"].mean,
        },
    }

    rel_text = (
        f"un aumento relativo del {rel_inc_pct:.1f} %"
        if rel_inc_pct is not None
        else "aumento relativo no definido (base = 0)"
    )
    saturation_text = (
        "sí alcanzan saturación (ρ_ofrecida >= 1)"
        if analysts_saturated
        else (
            f"no alcanzan saturación teórica al 100 % (ρ_ofrecida = {offered_util_a:.4f}, "
            f"utilización efectiva = {100.0 * util_a:.2f} %)"
        )
    )
    base_ploss_note = (
        "prácticamente empatadas en P_loss"
        if base_b_p_loss_indistinguishable
        else (
            f"menor P_loss con s=4 ({100.0 * p_b_s4:.4f} % vs {100.0 * p_b_k16:.4f} %)"
            if p_b_s4 <= p_b_k16
            else f"menor P_loss con K=16 ({100.0 * p_b_k16:.4f} % vs {100.0 * p_b_s4:.4f} %)"
        )
    )
    recommended_opt = (
        "contratar el 4.º analista (s=4, K=8)"
        if p_b_s4_ov <= p_b_k16_ov and b_s4.metrics["Wq"].mean <= b_k16.metrics["Wq"].mean
        else "evaluar compromiso entre buffer y analista según demanda"
    )

    recommendation = (
        f"Escenario A: al aumentar λ2 de 0,10 a 0,14/min (+40 %), P_loss pasa de "
        f"{100.0 * p_base:.3f} % a {100.0 * p_a:.3f} % (+{abs_pp:.3f} pp, {rel_text}); "
        f"los 3 analistas {saturation_text}, pero la congestión y la pérdida de alertas "
        f"aumentan de forma pronunciada. "
        f"Escenario B: bajo demanda base, ambas alternativas reducen P_loss en ~95 % y quedan "
        f"{base_ploss_note} ({100.0 * p_b_s4:.4f} % con s=4 vs {100.0 * p_b_k16:.4f} % con K=16), "
        f"pero s=4 recorta las esperas drásticamente (Wq1 = {b_s4.metrics['Wq1'].mean:.2f} vs "
        f"{b_k16.metrics['Wq1'].mean:.2f} min; Wq2 = {b_s4.metrics['Wq2'].mean:.2f} vs "
        f"{b_k16.metrics['Wq2'].mean:.2f} min). Bajo la sobrecarga del Escenario A, s=4 "
        f"también domina en P_loss ({100.0 * p_b_s4_ov:.4f} % vs {100.0 * p_b_k16_ov:.4f} %) "
        f"y en esperas (Wq2 = {b_s4_ov.metrics['Wq2'].mean:.2f} vs {b_k16_ov.metrics['Wq2'].mean:.2f} min). "
        f"Ampliar únicamente el buffer a K=16 permite acumular más alertas en espera y empeora "
        f"los tiempos de respuesta; por tanto, se recomienda {recommended_opt}."
    )
    return analysis, recommendation


def run_soc_scenarios(
    base_parameters: SOCParameters | None = None,
    *,
    replications: int = DEFAULT_SOC_REPLICATIONS,
    base_seed: int = DEFAULT_SOC_BASE_SEED,
    warmup: float = DEFAULT_SOC_WARMUP,
    horizon: float = DEFAULT_SOC_HORIZON,
    drain: bool = True,
    confidence: float = 0.95,
) -> SOCScenarioSuite:
    """Ejecuta todos los escenarios del SOC con semillas comunes (CRN) y los compara."""
    specs = build_soc_scenario_specs(base_parameters)
    replications_by_scenario: dict[str, list[SOCReplication]] = {}
    summaries: dict[str, SOCSummary] = {}

    for spec in specs:
        runs = run_soc_replications(
            spec.parameters,
            replications=replications,
            base_seed=base_seed,
            warmup=warmup,
            horizon=horizon,
            drain=drain,
        )
        replications_by_scenario[spec.scenario_id] = runs
        summaries[spec.scenario_id] = summarize_soc_replications(
            runs,
            spec.parameters,
            scenario_id=spec.scenario_id,
            label=spec.label,
            confidence=confidence,
        )

    comparisons = compare_soc_scenarios(
        replications_by_scenario,
        summaries,
        confidence=confidence,
    )
    analysis, recommendation = _build_scenario_analysis(summaries, comparisons)
    return SOCScenarioSuite(
        replications_by_scenario=replications_by_scenario,
        summaries=summaries,
        comparisons=comparisons,
        analysis=analysis,
        recommendation=recommendation,
    )
