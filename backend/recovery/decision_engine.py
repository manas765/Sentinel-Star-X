from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .memory import NetworkMemory
from .knowledge_base import RecoveryKnowledgeBase
from .cost_estimator import RecoveryCostEstimator, CostFactors
from .strategy_simulator import RecoveryStrategySimulator, SimulationResult
from .context_aware_recovery import RecoveryContext, RecoveryDecision, ContextAwareRecovery
import uuid
from datetime import datetime, timezone


class ObjectiveWeights(BaseModel):
    """How much each objective matters — must sum to 1.0."""
    speed: float = 0.30         # minimise recovery time
    reliability: float = 0.40  # maximise success probability
    cost: float = 0.20          # minimise total cost score
    safety: float = 0.10        # prefer strategies with rollback


class EngineDecision(BaseModel):
    """Final decision output from the Decision Engine."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    failed_node: str
    chosen_strategy: str
    composite_score: float          # higher = better (0–100)
    simulation: SimulationResult
    weights_used: ObjectiveWeights
    runner_up: Optional[str] = None
    reasoning: str


class MultiObjectiveDecisionEngine:
    """
    Feature #22 — Multi-Objective Decision Engine.

    Scores every candidate strategy across multiple objectives
    (speed, reliability, cost, safety) and picks the one with
    the highest weighted composite score.

    This is the single entry point the Autonomous Self-Healing
    module (#27) and Human-in-the-Loop (#45) call.
    """

    def __init__(
        self,
        memory: NetworkMemory,
        weights: Optional[ObjectiveWeights] = None,
    ) -> None:
        self._memory = memory
        self._weights = weights or ObjectiveWeights()
        self._simulator = RecoveryStrategySimulator(memory)
        self._kb = RecoveryKnowledgeBase(memory)

    def _score(
        self,
        sim: SimulationResult,
        weights: ObjectiveWeights,
    ) -> float:
        """Compute weighted composite score (0–100, higher = better)."""
        # Speed: invert duration (cap at 60s for normalisation)
        max_duration = 60.0
        speed_score = max(0.0, 1.0 - sim.projected_duration_seconds / max_duration) * 100

        # Reliability: success probability directly
        reliability_score = sim.projected_success_probability * 100

        # Cost: invert recommendation_score (lower cost = higher score)
        cost_score = max(0.0, 100.0 - sim.decision.estimated_cost.recommendation_score)

        # Safety: rollback available = 100, not available = 0
        safety_score = 100.0 if sim.decision.estimated_cost.rollback_bonus > 0 else 0.0

        composite = (
            speed_score       * weights.speed +
            reliability_score * weights.reliability +
            cost_score        * weights.cost +
            safety_score      * weights.safety
        )
        return round(composite, 2)

    def decide(
        self,
        node_id: str,
        context: RecoveryContext,
        weights: Optional[ObjectiveWeights] = None,
    ) -> EngineDecision:
        w = weights or self._weights

        # Simulate all strategies
        simulations = self._simulator.simulate_all_strategies(node_id, context)

        # Score each one
        scored = [
            (sim, self._score(sim, w))
            for sim in simulations
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        best_sim, best_score = scored[0]
        runner_up = scored[1][0].strategy if len(scored) > 1 else None

        reasoning = (
            f"Chose '{best_sim.strategy}' for node {node_id} "
            f"with composite score {best_score}/100. "
            f"Success probability: {best_sim.projected_success_probability:.0%}. "
            f"Projected duration: {best_sim.projected_duration_seconds:.1f}s. "
            f"{'Runner-up: ' + runner_up + '.' if runner_up else ''}"
        )

        return EngineDecision(
            failed_node=node_id,
            chosen_strategy=best_sim.strategy,
            composite_score=best_score,
            simulation=best_sim,
            weights_used=w,
            runner_up=runner_up,
            reasoning=reasoning,
        )

    def decide_all(
        self,
        context: RecoveryContext,
        weights: Optional[ObjectiveWeights] = None,
    ) -> List[EngineDecision]:
        """Make decisions for every failed node in the context."""
        return [self.decide(node, context, weights) for node in context.failed_nodes]

    def update_weights(self, weights: ObjectiveWeights) -> None:
        """Let Human-in-the-Loop (#45) adjust priorities at runtime."""
        self._weights = weights
