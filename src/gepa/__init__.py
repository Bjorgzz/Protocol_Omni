"""
GEPA Evolution System for Protocol OMNI v14.0 SOVEREIGN GENESIS

Genetic-Pareto prompt optimization via natural language reflection.
Outperforms GRPO (RL) by 10% average, 20% max, with 35x fewer rollouts.
"""

from .evolution import GEPAEvolutionEngine, PromptVariant, Reflection, Trajectory
from .pareto import ParetoFrontier

__all__ = [
    "GEPAEvolutionEngine",
    "PromptVariant",
    "Trajectory",
    "Reflection",
    "ParetoFrontier",
]
