from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .context_aware_recovery import RecoveryContext, RecoveryDecision, ContextAwareRecovery
from .memory import NetworkMemory
from .models import NetworkSnapshot, RecoveryEvent
import uuid
from datetime import datetime, timezone


class SimulationResult(BaseModel):
    """Outcome of simulating one strategy against a network context."""
    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    strategy: str
    context_snapshot: Dict
    decision: RecoveryDecision
    projected_success_probability: float   # 0.0 – 1.0
    projected_duration_seconds: float
    warnings: List[str] = []


class RecoveryStrategySimulator:
    """
    Feature #21 — Recovery Strategy Simulator.

    Lets you simulate 'what would happen if we tried strategy X
    on this network?' without executing anything real.
    Used by the Decision Engine and the Command Center dashboard.
    """

    # Rough success probability per strategy under ideal conditions
    BASE_SUCCESS_PROB: Dict[str, float] = {
        "reroute":  0.90,
        "restart":  0.70,
        "failover": 0.80,
        "isolate":  0.95,
    }

    def __init__(self, memory: NetworkMemory) -> None:
        self._memory = memory
        self._car = ContextAwareRecovery(memory)
        self._history: List[SimulationResult] = []

    def _adjust_probability(
        self,
        strategy: str,
        context: RecoveryContext,
        node_id: str,
    ) -> float:
        base = self.BASE_SUCCESS_PROB.get(strategy, 0.60)

        # High load reduces success probability
        base -= context.network_load * 0.20

        # Untrusted nodes are risky regardless of strategy
        trust = context.trust_levels.get(node_id, "NORMAL")
        if trust == "UNTRUSTED":
            base -= 0.30
        elif trust == "SUSPICIOUS":
            base -= 0.15

        # History boosts confidence
        from .knowledge_base import RecoveryKnowledgeBase
        kb = RecoveryKnowledgeBase(self._memory)
        rate = self._memory.strategy_success_rate(strategy)
        if rate > 0:
            base = base * 0.6 + rate * 0.4   # blend base + historical

        return round(max(0.0, min(1.0, base)), 3)

    def _collect_warnings(
        self,
        strategy: str,
        context: RecoveryContext,
        node_id: str,
    ) -> List[str]:
        warnings = []
        if context.network_load > 0.8:
            warnings.append("Network load is critically high — recovery may be slow.")
        trust = context.trust_levels.get(node_id, "NORMAL")
        if trust == "UNTRUSTED":
            warnings.append(f"Node {node_id} is UNTRUSTED — security team should review first.")
        if trust == "SUSPICIOUS":
            warnings.append(f"Node {node_id} is SUSPICIOUS — manual verification recommended.")
        if strategy == "restart" and len(context.active_services) > 3:
            warnings.append("Restart will briefly drop all active services on this node.")
        return warnings

    def simulate(self, node_id: str, strategy: str, context: RecoveryContext) -> SimulationResult:
        """Simulate a specific strategy for a specific node."""
        # Force the context to use only the given strategy
        forced_context = context.model_copy(
            update={"candidate_strategies": [strategy]}
        )
        decision = self._car.decide(node_id, forced_context)

        prob = self._adjust_probability(strategy, context, node_id)
        from .cost_estimator import RecoveryCostEstimator, CostFactors
        est = RecoveryCostEstimator()
        factors = CostFactors(
            strategy=strategy,
            affected_nodes=[node_id],
            estimated_duration_seconds=decision.estimated_cost.time_cost / 0.25 if decision.estimated_cost.time_cost > 0 else 5.0,
            service_downtime_seconds=decision.estimated_cost.downtime_cost / 0.25 if decision.estimated_cost.downtime_cost > 0 else 2.0,
            risk_of_failure=1.0 - prob,
            rollback_available=(strategy != "isolate"),
        )
        projected_duration = factors.estimated_duration_seconds * (1.0 + context.network_load)

        result = SimulationResult(
            strategy=strategy,
            context_snapshot={
                "failed_nodes": context.failed_nodes,
                "network_load": context.network_load,
                "active_services": context.active_services,
                "trust": context.trust_levels.get(node_id, "NORMAL"),
            },
            decision=decision,
            projected_success_probability=prob,
            projected_duration_seconds=round(projected_duration, 2),
            warnings=self._collect_warnings(strategy, context, node_id),
        )
        self._history.append(result)
        return result

    def simulate_all_strategies(
        self, node_id: str, context: RecoveryContext
    ) -> List[SimulationResult]:
        """Simulate every candidate strategy and return ranked by success probability."""
        results = [
            self.simulate(node_id, s, context)
            for s in context.candidate_strategies
        ]
        return sorted(results, key=lambda r: r.projected_success_probability, reverse=True)

    def best_simulation(
        self, node_id: str, context: RecoveryContext
    ) -> Optional[SimulationResult]:
        results = self.simulate_all_strategies(node_id, context)
        return results[0] if results else None

    def simulation_history(self) -> List[SimulationResult]:
        return list(self._history)
