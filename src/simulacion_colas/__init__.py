"""Paquete de simulación de colas.

El proyecto implementa un motor de eventos discretos y dos modelos:
un servidor M/M/1 y un centro de triaje SOC con prioridades y buffer finito.
"""

from .engine import Event, EventQueue, Simulation

__version__ = "0.1.0"

__all__ = ["Event", "EventQueue", "Simulation", "__version__"]
