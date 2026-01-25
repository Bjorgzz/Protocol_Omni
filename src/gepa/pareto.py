"""
Pareto Frontier utilities for multi-objective optimization.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Solution:
    """A solution in the objective space."""
    id: str
    objectives: Dict[str, float]
    data: Any = None

    def dominates(self, other: "Solution", minimize: Optional[List[str]] = None) -> bool:
        """
        Check if this solution Pareto-dominates another.

        Args:
            other: Another solution to compare against
            minimize: List of objectives to minimize (default: maximize all)

        Returns:
            True if this solution dominates the other
        """
        minimize = minimize or []

        common = set(self.objectives.keys()) & set(other.objectives.keys())
        if not common:
            return False

        at_least_one_better = False
        for obj in common:
            self_val = self.objectives[obj]
            other_val = other.objectives[obj]

            if obj in minimize:
                if self_val > other_val:
                    return False
                if self_val < other_val:
                    at_least_one_better = True
            else:
                if self_val < other_val:
                    return False
                if self_val > other_val:
                    at_least_one_better = True

        return at_least_one_better


class ParetoFrontier:
    """
    Maintains a Pareto frontier of non-dominated solutions.
    """

    def __init__(
        self,
        max_size: int = 10,
        minimize: Optional[List[str]] = None,
    ):
        self.max_size = max_size
        self.minimize = minimize or []
        self.solutions: List[Solution] = []
        self.logger = logging.getLogger(__name__)

    def add(self, solution: Solution) -> bool:
        """
        Try to add a solution to the frontier.

        Args:
            solution: Solution to add

        Returns:
            True if solution was added (is non-dominated)
        """
        for existing in self.solutions:
            if existing.dominates(solution, self.minimize):
                return False

        self.solutions = [
            s for s in self.solutions
            if not solution.dominates(s, self.minimize)
        ]

        self.solutions.append(solution)

        if len(self.solutions) > self.max_size:
            self._prune()

        return True

    def _prune(self):
        """Prune frontier to max_size using crowding distance."""
        if len(self.solutions) <= self.max_size:
            return

        crowding = self._calculate_crowding_distances()

        sorted_solutions = sorted(
            zip(self.solutions, crowding),
            key=lambda x: x[1],
            reverse=True,
        )

        self.solutions = [s for s, _ in sorted_solutions[:self.max_size]]

    def _calculate_crowding_distances(self) -> List[float]:
        """Calculate crowding distance for each solution."""
        n = len(self.solutions)
        if n == 0:
            return []

        distances = [0.0] * n

        if not self.solutions[0].objectives:
            return distances

        objectives = list(self.solutions[0].objectives.keys())

        for obj in objectives:
            sorted_indices = sorted(
                range(n),
                key=lambda i: self.solutions[i].objectives.get(obj, 0),
            )

            distances[sorted_indices[0]] = float('inf')
            distances[sorted_indices[-1]] = float('inf')

            obj_values = [
                self.solutions[i].objectives.get(obj, 0)
                for i in sorted_indices
            ]
            obj_range = max(obj_values) - min(obj_values)

            if obj_range == 0:
                continue

            for i in range(1, n - 1):
                distances[sorted_indices[i]] += (
                    obj_values[i + 1] - obj_values[i - 1]
                ) / obj_range

        return distances

    def get_best(self, objective: str) -> Optional[Solution]:
        """Get the best solution for a specific objective."""
        if not self.solutions:
            return None

        if objective in self.minimize:
            return min(
                self.solutions,
                key=lambda s: s.objectives.get(objective, float('inf')),
            )
        else:
            return max(
                self.solutions,
                key=lambda s: s.objectives.get(objective, float('-inf')),
            )

    def get_compromise(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[Solution]:
        """
        Get a compromise solution using weighted sum.

        Args:
            weights: Dict of objective -> weight (default: equal weights)

        Returns:
            The solution with best weighted sum
        """
        if not self.solutions:
            return None

        if weights is None:
            objectives = list(self.solutions[0].objectives.keys())
            weights = {obj: 1.0 / len(objectives) for obj in objectives}

        def weighted_score(solution: Solution) -> float:
            score = 0.0
            for obj, weight in weights.items():
                val = solution.objectives.get(obj, 0)
                if obj in self.minimize:
                    score -= weight * val
                else:
                    score += weight * val
            return score

        return max(self.solutions, key=weighted_score)

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert frontier to list of dicts."""
        return [
            {"id": s.id, "objectives": s.objectives, "data": s.data}
            for s in self.solutions
        ]

    def __len__(self) -> int:
        return len(self.solutions)

    def __iter__(self):
        return iter(self.solutions)
