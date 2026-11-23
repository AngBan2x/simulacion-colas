"""Paquete de simulación de colas.

El proyecto implementa un motor de eventos discretos y dos modelos:
un servidor M/M/1 y un centro de triaje SOC con prioridades y buffer finito.
"""

from .distributions import Exponential, Uniform, Weibull, spawn_streams
from .engine import Event, EventQueue, Simulation
from .mm1 import MM1Analytical, MM1Parameters, MM1Replication, simulate_replication
from .soc import (
    SOCComparisonMetric,
    SOCParameters,
    SOCReplication,
    SOCScenarioSpec,
    SOCScenarioSuite,
    SOCScriptedArrival,
    SOCServiceRecord,
    SOCSummary,
    run_soc_replications,
    run_soc_scenarios,
    simulate_soc_replication,
    simulate_soc_scripted,
    summarize_soc_replications,
)
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
    "SOCComparisonMetric",
    "SOCParameters",
    "SOCReplication",
    "SOCScenarioSpec",
    "SOCScenarioSuite",
    "SOCScriptedArrival",
    "SOCServiceRecord",
    "SOCSummary",
    "Simulation",
    "TimeWeightedAccumulator",
    "Uniform",
    "Weibull",
    "run_soc_replications",
    "run_soc_scenarios",
    "simulate_replication",
    "simulate_soc_replication",
    "simulate_soc_scripted",
    "spawn_streams",
    "summarize",
    "summarize_soc_replications",
    "__version__",
]
