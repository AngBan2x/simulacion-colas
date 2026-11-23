"""Paquete de simulación de colas.

El proyecto implementa un motor de eventos discretos y dos modelos:
un servidor M/M/1 y un centro de triaje SOC con prioridades y buffer finito.
"""

from .distributions import Exponential, Uniform, Weibull, spawn_streams
from .engine import Event, EventQueue, Simulation
from .mm1 import MM1Analytical, MM1Parameters, MM1Replication, simulate_replication
from .stats import ConfidenceInterval, TimeWeightedAccumulator, summarize

__version__ = "0.2.0"

__all__ = [
    "ConfidenceInterval",
    "Event",
    "EventQueue",
    "Exponential",
    "MM1Analytical",
    "MM1Parameters",
    "MM1Replication",
    "Simulation",
    "TimeWeightedAccumulator",
    "Uniform",
    "Weibull",
    "simulate_replication",
    "spawn_streams",
    "summarize",
    "__version__",
]
