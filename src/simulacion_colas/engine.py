"""Motor de eventos discretos para los modelos de simulación.

El motor mantiene un reloj, una cola de eventos ordenada por tiempo y un
conjunto de callbacks. La regla de desempate es:

1. menor tiempo;
2. menor valor de ``priority`` (los valores más pequeños se procesan antes);
3. menor número de secuencia (FIFO entre eventos programados con el mismo
   tiempo y prioridad).

Los modelos pueden usar ``priority`` para definir, por ejemplo, que una salida
de servicio se procese antes que una llegada en el mismo instante.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import count
from math import isfinite
from typing import Callable

Callback = Callable[[], None]


@dataclass(frozen=True, slots=True)
class Event:
    """Evento programado en el motor.

    ``sequence`` se asigna automáticamente al programar el evento y garantiza
    un orden determinista cuando dos eventos tienen el mismo tiempo y prioridad.
    """

    time: float
    priority: int
    sequence: int
    kind: str
    callback: Callback = field(compare=False, repr=False)


class EventQueue:
    """Cola prioritaria de eventos basada en ``heapq``."""

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, int, Event]] = []
        self._sequence = count()

    def schedule(
        self,
        time: float,
        callback: Callback,
        *,
        priority: int = 0,
        kind: str = "event",
    ) -> Event:
        """Programa un evento en un tiempo absoluto."""
        event_time = float(time)
        if not isfinite(event_time):
            raise ValueError("El tiempo del evento debe ser finito.")

        event = Event(
            time=event_time,
            priority=int(priority),
            sequence=next(self._sequence),
            kind=kind,
            callback=callback,
        )
        heappush(
            self._heap,
            (event.time, event.priority, event.sequence, event),
        )
        return event

    def peek(self) -> Event | None:
        """Devuelve el próximo evento sin extraerlo, o ``None`` si está vacía."""
        return self._heap[0][3] if self._heap else None

    def pop(self) -> Event:
        """Extrae y devuelve el próximo evento."""
        if not self._heap:
            raise IndexError("No quedan eventos en la cola.")
        return heappop(self._heap)[3]

    def clear(self) -> None:
        """Vacía la cola de eventos."""
        self._heap.clear()

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)


class Simulation:
    """Reloj de simulación y bucle principal de eventos discretos."""

    def __init__(self, start_time: float = 0.0) -> None:
        initial_time = float(start_time)
        if not isfinite(initial_time):
            raise ValueError("El tiempo inicial debe ser finito.")
        if initial_time < 0:
            raise ValueError("El tiempo inicial no puede ser negativo.")

        self._now = initial_time
        self._events = EventQueue()
        self._stopped = False

    @property
    def now(self) -> float:
        """Tiempo actual de la simulación."""
        return self._now

    @property
    def pending_events(self) -> int:
        """Cantidad de eventos pendientes."""
        return len(self._events)

    def schedule(
        self,
        delay: float,
        callback: Callback,
        *,
        priority: int = 0,
        kind: str = "event",
    ) -> Event:
        """Programa un evento ``delay`` unidades después del tiempo actual."""
        event_delay = float(delay)
        if not isfinite(event_delay):
            raise ValueError("El retardo debe ser finito.")
        if event_delay < 0:
            raise ValueError("El retardo no puede ser negativo.")
        return self._events.schedule(
            self._now + event_delay,
            callback,
            priority=priority,
            kind=kind,
        )

    def schedule_at(
        self,
        time: float,
        callback: Callback,
        *,
        priority: int = 0,
        kind: str = "event",
    ) -> Event:
        """Programa un evento en un tiempo absoluto no anterior al actual."""
        event_time = float(time)
        if not isfinite(event_time):
            raise ValueError("El tiempo del evento debe ser finito.")
        if event_time < self._now:
            raise ValueError("No se pueden programar eventos en el pasado.")
        return self._events.schedule(
            event_time,
            callback,
            priority=priority,
            kind=kind,
        )

    def stop(self) -> None:
        """Solicita detener el bucle después del callback actual."""
        self._stopped = True

    def run(self, until: float | None = None) -> None:
        """Ejecuta eventos hasta ``until`` o hasta que no queden eventos.

        Si ``until`` es ``None``, se procesan todos los eventos pendientes. Los
        eventos programados exactamente en ``until`` sí se procesan. Si el
        próximo evento ocurre después de ``until``, el reloj avanza hasta
        ``until`` y el evento permanece en la cola.
        """
        if until is not None:
            limit = float(until)
            if not isfinite(limit):
                raise ValueError("El límite de tiempo debe ser finito.")
            if limit < self._now:
                raise ValueError("El límite no puede ser anterior al tiempo actual.")
        else:
            limit = None

        self._stopped = False

        while True:
            next_event = self._events.peek()
            if next_event is None:
                if limit is not None:
                    self._now = limit
                return

            if limit is not None and next_event.time > limit:
                self._now = limit
                return

            event = self._events.pop()
            if event.time < self._now:
                raise RuntimeError(
                    "Se encontró un evento en el pasado; el reloj no es monotónico."
                )

            self._now = event.time
            event.callback()

            if self._stopped:
                self._stopped = False
                return
