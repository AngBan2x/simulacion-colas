from __future__ import annotations

import pytest

from simulacion_colas.distributions import Exponential, spawn_streams
from simulacion_colas.engine import EventQueue, Simulation


def test_events_run_in_time_order() -> None:
    simulation = Simulation()
    processed: list[str] = []

    simulation.schedule(2.0, lambda: processed.append("segundo"), kind="test")
    simulation.schedule(1.0, lambda: processed.append("primero"), kind="test")
    simulation.schedule(3.0, lambda: processed.append("tercero"), kind="test")

    simulation.run()

    assert processed == ["primero", "segundo", "tercero"]
    assert simulation.now == 3.0
    assert simulation.pending_events == 0


def test_tie_break_uses_priority_then_fifo() -> None:
    simulation = Simulation()
    processed: list[str] = []

    simulation.schedule(1.0, lambda: processed.append("prioridad-5"), priority=5)
    simulation.schedule(1.0, lambda: processed.append("prioridad-0-a"), priority=0)
    simulation.schedule(1.0, lambda: processed.append("prioridad-0-b"), priority=0)
    simulation.schedule(1.0, lambda: processed.append("prioridad-1"), priority=1)

    simulation.run()

    assert processed == [
        "prioridad-0-a",
        "prioridad-0-b",
        "prioridad-1",
        "prioridad-5",
    ]


def test_run_until_leaves_future_events_pending() -> None:
    simulation = Simulation()
    processed: list[float] = []

    simulation.schedule(1.0, lambda: processed.append(simulation.now))
    simulation.schedule(5.0, lambda: processed.append(simulation.now))

    simulation.run(until=3.0)

    assert processed == [1.0]
    assert simulation.now == 3.0
    assert simulation.pending_events == 1

    simulation.run()

    assert processed == [1.0, 5.0]
    assert simulation.now == 5.0


def test_run_without_events_advances_to_limit() -> None:
    simulation = Simulation()

    simulation.run(until=7.5)

    assert simulation.now == 7.5
    assert simulation.pending_events == 0


def test_callbacks_can_schedule_more_events() -> None:
    simulation = Simulation()
    processed: list[str] = []

    def first() -> None:
        processed.append("primero")
        simulation.schedule(1.0, lambda: processed.append("segundo"))

    simulation.schedule(0.0, first)
    simulation.run()

    assert processed == ["primero", "segundo"]
    assert simulation.now == 1.0


def test_stop_prevents_processing_remaining_events() -> None:
    simulation = Simulation()
    processed: list[str] = []

    def first() -> None:
        processed.append("primero")
        simulation.stop()

    simulation.schedule(1.0, first)
    simulation.schedule(2.0, lambda: processed.append("no debe ejecutarse"))

    simulation.run()

    assert processed == ["primero"]
    assert simulation.now == 1.0
    assert simulation.pending_events == 1


def test_negative_delay_is_rejected() -> None:
    simulation = Simulation()

    with pytest.raises(ValueError, match="retardo"):
        simulation.schedule(-1.0, lambda: None)


def test_event_in_the_past_is_rejected() -> None:
    simulation = Simulation()
    simulation.run(until=10.0)

    with pytest.raises(ValueError, match="pasado"):
        simulation.schedule_at(5.0, lambda: None)


def test_streams_reproduce_event_sequences() -> None:
    def run(seed: int) -> list[float]:
        streams = spawn_streams(seed, ("llegadas", "servicios"))
        events = Simulation()
        times: list[float] = []

        def arrival() -> None:
            times.append(events.now)
            if len(times) < 10:
                delay = Exponential(0.25).sample(streams["llegadas"])
                events.schedule(delay, arrival)

        events.schedule(0.0, arrival)
        events.run()
        return times

    assert run(42) == run(42)
    assert run(42) != run(43)


def test_event_queue_exposes_next_event() -> None:
    queue = EventQueue()

    assert queue.peek() is None
    assert len(queue) == 0

    event = queue.schedule(3.0, lambda: None, priority=2, kind="prueba")

    assert queue.peek() is event
    assert len(queue) == 1
    assert queue.pop() is event
    assert queue.peek() is None
