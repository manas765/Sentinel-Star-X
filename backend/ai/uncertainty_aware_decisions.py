"""
backend/ai/uncertainty_aware_decisions.py

Feature 16/16 (global #60): Uncertainty-Aware Autonomous Decisions.

Last feature on the track -- this is the policy layer that decides HOW
autonomously the system should act, not WHAT to do (that's Aakash's
Decision Engine) or whether the diagnosis is solid (Feature 12, which this
builds directly on). Combines recovery confidence + severity + the
"symptom, not root cause" signal into one of four autonomy levels per
target.

This is also the answer to the Feature 15 question (should adaptive
thresholds auto-apply): yes, but only when THIS feature says AUTONOMOUS
for that decision -- otherwise it goes through as REQUIRES_APPROVAL or
HOLD. Nothing in adaptive_thresholds.py needs to change for that; whatever
calls get_node_threshold_config() can route the swap decision through
decide_autonomy() instead of applying it unconditionally.

Feeds Aakash's Decision Engine the same way Recovery Confidence does --
per your own roadmap, these two were always meant to land together.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.ai.recovery_confidence import evaluate_recovery_confidence
from backend.network.models import Topology


class AutonomyLevel(str, Enum):
    AUTONOMOUS = "autonomous"
    AUTONOMOUS_NOTIFY = "autonomous_notify"
    REQUIRES_APPROVAL = "requires_approval"
    HOLD = "hold"


@dataclass
class DecisionResult:
    target_id: str
    target_type: str
    autonomy_level: str
    uncertainty_score: float
    reasoning: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class UncertaintyAwareDecisionEngine:
    """
    Policy (tunable):
      symptom, not root cause          -> REQUIRES_APPROVAL, always, regardless of confidence
      uncertainty < autonomous_ceiling and severity == critical -> AUTONOMOUS
      uncertainty < autonomous_ceiling (not critical)           -> AUTONOMOUS_NOTIFY
      uncertainty < approval_ceiling                            -> REQUIRES_APPROVAL
      otherwise                                                 -> HOLD
    """

    def __init__(self, autonomous_uncertainty_ceiling: float = 0.15, approval_uncertainty_ceiling: float = 0.4):
        self.autonomous_ceiling = autonomous_uncertainty_ceiling
        self.approval_ceiling = approval_uncertainty_ceiling

    def decide(self, node_anomaly_results: list, link_anomaly_results: list, topology: Topology, central_node_id: str) -> list:
        confidence_results = evaluate_recovery_confidence(
            node_anomaly_results, link_anomaly_results, topology, central_node_id
        )
        severity_by_id = {r["node_id"]: r["severity"] for r in node_anomaly_results}
        severity_by_id.update({r["link_id"]: r["severity"] for r in link_anomaly_results})

        return [self._decide_one(r, severity_by_id.get(r["target_id"], "none")) for r in confidence_results]

    def _decide_one(self, confidence_result: dict, severity: str) -> DecisionResult:
        target_id = confidence_result["target_id"]
        target_type = confidence_result["target_type"]
        recommendation = confidence_result["recommendation"]
        recovery_confidence = confidence_result["recovery_confidence"]

        if recommendation == "no_action_needed":
            return DecisionResult(
                target_id=target_id, target_type=target_type,
                autonomy_level=AutonomyLevel.HOLD.value, uncertainty_score=0.0,
                reasoning="Nothing anomalous -- no decision needed.",
            )

        if recommendation == "act_on_root_cause_instead":
            return DecisionResult(
                target_id=target_id, target_type=target_type,
                autonomy_level=AutonomyLevel.REQUIRES_APPROVAL.value,
                uncertainty_score=round(1 - recovery_confidence, 3),
                reasoning=(
                    f"{target_id} is a symptom, not a root cause ({confidence_result['points_to']}). "
                    f"Never autonomous -- acting on a symptom needs human judgment on whether "
                    f"the real root cause is also being handled."
                ),
            )

        uncertainty = round(1 - recovery_confidence, 3)

        if uncertainty < self.autonomous_ceiling and severity == "critical":
            level = AutonomyLevel.AUTONOMOUS
            reasoning = f"High confidence ({recovery_confidence}) and critical severity -- safe to act without waiting on a human."
        elif uncertainty < self.autonomous_ceiling:
            level = AutonomyLevel.AUTONOMOUS_NOTIFY
            reasoning = f"High confidence ({recovery_confidence}) but not critical severity -- act, but notify rather than act silently."
        elif uncertainty < self.approval_ceiling:
            level = AutonomyLevel.REQUIRES_APPROVAL
            reasoning = f"Moderate confidence ({recovery_confidence}) -- propose the action, wait for sign-off."
        else:
            level = AutonomyLevel.HOLD
            reasoning = f"Low confidence ({recovery_confidence}) -- not enough signal to act or propose yet."

        return DecisionResult(
            target_id=target_id, target_type=target_type,
            autonomy_level=level.value, uncertainty_score=uncertainty, reasoning=reasoning,
        )


def decide_autonomy(node_anomaly_results, link_anomaly_results, topology, central_node_id, engine=None) -> list:
    """Convenience entry point. Returns JSON-able list[dict]."""
    engine = engine or UncertaintyAwareDecisionEngine()
    return [d.to_dict() for d in engine.decide(node_anomaly_results, link_anomaly_results, topology, central_node_id)]