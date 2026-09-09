from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CostFactors(BaseModel):
    """Inputs that drive cost calculation for a recovery action."""
    strategy: str
    affected_nodes: List[str]
    estimated_duration_seconds: float
    service_downtime_seconds: float
    risk_of_failure: float          # 0.0 – 1.0
    manual_intervention_required: bool = False
    rollback_available: bool = True


class CostEstimate(BaseModel):
    """Output of the cost estimator for one strategy."""
    strategy: str
    time_cost: float        # weighted duration score
    risk_cost: float        # penalty for chance of failure
    downtime_cost: float    # penalty for service impact
    manual_cost: float      # penalty if humans must intervene
    rollback_bonus: float   # discount for having a safe rollback
    total_cost: float
    recommendation_score: float   # lower is better; 0–100 normalised


class RecoveryCostEstimator:
    """
    Feature #43 — Recovery Cost Estimator.

    Scores each candidate strategy on time, risk, downtime, and
    human effort so the Decision Engine (#22) can pick the
    least-costly option, not just the historically best one.
    """

    # Weights — tweak these as the project matures
    W_TIME     = 0.25
    W_RISK     = 0.35
    W_DOWNTIME = 0.25
    W_MANUAL   = 0.15
    ROLLBACK_DISCOUNT = 10.0
    MANUAL_PENALTY    = 20.0

    def estimate(self, factors: CostFactors) -> CostEstimate:
        time_cost     = factors.estimated_duration_seconds * self.W_TIME
        risk_cost     = factors.risk_of_failure * 100 * self.W_RISK
        downtime_cost = factors.service_downtime_seconds * self.W_DOWNTIME
        manual_cost   = self.MANUAL_PENALTY if factors.manual_intervention_required else 0.0
        rollback_bonus = self.ROLLBACK_DISCOUNT if factors.rollback_available else 0.0

        total = time_cost + risk_cost + downtime_cost + manual_cost - rollback_bonus
        total = max(total, 0.0)

        # Normalise to 0–100 (cap at 200 raw before scaling)
        recommendation_score = min(total / 200.0, 1.0) * 100

        return CostEstimate(
            strategy=factors.strategy,
            time_cost=round(time_cost, 2),
            risk_cost=round(risk_cost, 2),
            downtime_cost=round(downtime_cost, 2),
            manual_cost=manual_cost,
            rollback_bonus=rollback_bonus,
            total_cost=round(total, 2),
            recommendation_score=round(recommendation_score, 2),
        )

    def compare(self, options: List[CostFactors]) -> List[CostEstimate]:
        """Estimate all options and return sorted cheapest-first."""
        estimates = [self.estimate(f) for f in options]
        return sorted(estimates, key=lambda e: e.total_cost)

    def cheapest(self, options: List[CostFactors]) -> Optional[CostEstimate]:
        """Return the single lowest-cost option."""
        ranked = self.compare(options)
        return ranked[0] if ranked else None
