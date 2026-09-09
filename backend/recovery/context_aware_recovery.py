from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .memory import NetworkMemory
from .knowledge_base import RecoveryKnowledgeBase
from .cost_estimator import RecoveryCostEstimator, CostFactors, CostEstimate


class RecoveryContext(BaseModel):
    """Everything known about the current failure situation."""
    failed_nodes: List[str]
    active_services: List[str]
    network_load: float = Field(ge=0.0, le=1.0)   # 0.0 = idle, 1.0 = saturated
    trust_levels: Dict[str, str] = {}              # node_id -> "TRUSTED"/"SUSPICIOUS" etc.
    candidate_strategies: List[str] = ["reroute", "restart", "failover", "isolate"]


class RecoveryDecision(BaseModel):
    """What the system decided and why."""
    failed_node: str
    chosen_strategy: str
    estimated_cost: CostEstimate
    history_based: bool        # True if knowledge base had prior data
    trust_blocked: bool = False
    reasoning: str


class ContextAwareRecovery:
    """
    Feature #23 — Context-Aware Recovery.

    Combines NetworkMemory + KnowledgeBase + CostEstimator to pick
    the best recovery strategy for each failed node given the
    current network situation (load, trust levels, active services).
    """

    # Risk adjustments based on context
    RISK_BASE: Dict[str, float] = {
        "reroute":  0.10,
        "restart":  0.35,
        "failover": 0.20,
        "isolate":  0.05,
    }
    DURATION_BASE: Dict[str, float] = {
        "reroute":  3.0,
        "restart":  15.0,
        "failover": 8.0,
        "isolate":  2.0,
    }

    def __init__(self, memory: NetworkMemory) -> None:
        self._memory = memory
        self._kb = RecoveryKnowledgeBase(memory)
        self._estimator = RecoveryCostEstimator()

    def _is_trust_blocked(self, node_id: str, trust_levels: Dict[str, str]) -> bool:
        """Block recovery if node is UNTRUSTED — defer to Manas's security gate."""
        return trust_levels.get(node_id) == "UNTRUSTED"

    def _build_factors(
        self,
        node_id: str,
        strategy: str,
        context: RecoveryContext,
    ) -> CostFactors:
        base_risk = self.RISK_BASE.get(strategy, 0.3)
        base_duration = self.DURATION_BASE.get(strategy, 10.0)

        # High network load increases risk and duration
        load_multiplier = 1.0 + context.network_load
        risk = min(base_risk * load_multiplier, 1.0)
        duration = base_duration * load_multiplier

        # Downtime estimate: longer for critical services
        downtime = duration * 0.5 if context.active_services else duration * 0.2

        # Manual intervention needed if node is suspicious
        trust = context.trust_levels.get(node_id, "NORMAL")
        manual = trust in ("SUSPICIOUS",)

        return CostFactors(
            strategy=strategy,
            affected_nodes=[node_id],
            estimated_duration_seconds=round(duration, 2),
            service_downtime_seconds=round(downtime, 2),
            risk_of_failure=round(risk, 3),
            manual_intervention_required=manual,
            rollback_available=(strategy != "isolate"),
        )

    def decide(self, node_id: str, context: RecoveryContext) -> RecoveryDecision:
        """Return the best recovery decision for a single failed node."""

        # Trust gate — if UNTRUSTED, block and let security team handle it
        if self._is_trust_blocked(node_id, context.trust_levels):
            dummy_factors = self._build_factors(node_id, "isolate", context)
            return RecoveryDecision(
                failed_node=node_id,
                chosen_strategy="isolate",
                estimated_cost=self._estimator.estimate(dummy_factors),
                history_based=False,
                trust_blocked=True,
                reasoning=f"Node {node_id} is UNTRUSTED — isolated pending security review.",
            )

        # Check knowledge base for historical best strategy
        kb_recommendation = self._kb.recommend(node_id)
        strategies = context.candidate_strategies

        # Build cost factors for every candidate strategy
        options = [self._build_factors(node_id, s, context) for s in strategies]
        ranked = self._estimator.compare(options)
        best_cost = ranked[0]

        # Prefer history-backed strategy if it's within 20% of cheapest cost
        chosen = best_cost.strategy
        history_used = False
        if kb_recommendation["has_history"]:
            hist_strategy = kb_recommendation["recommended_strategy"]
            hist_estimate = next((e for e in ranked if e.strategy == hist_strategy), None)
            if hist_estimate and hist_estimate.total_cost <= best_cost.total_cost * 1.2:
                chosen = hist_strategy
                best_cost = hist_estimate
                history_used = True

        reasoning = (
            f"Chose '{chosen}' for node {node_id}. "
            f"{'History-backed: previously successful. ' if history_used else 'Cost-optimised: no prior history. '}"
            f"Network load: {context.network_load:.0%}. "
            f"Trust: {context.trust_levels.get(node_id, 'NORMAL')}."
        )

        return RecoveryDecision(
            failed_node=node_id,
            chosen_strategy=chosen,
            estimated_cost=best_cost,
            history_based=history_used,
            trust_blocked=False,
            reasoning=reasoning,
        )

    def decide_all(self, context: RecoveryContext) -> List[RecoveryDecision]:
        """Make decisions for every failed node in the context."""
        return [self.decide(node, context) for node in context.failed_nodes]
