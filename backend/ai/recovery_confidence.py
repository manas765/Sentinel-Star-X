"""
backend/ai/recovery_confidence.py

Feature 12/16 (global #44): Recovery Confidence.

INTERFACE FLAG -- scope decision, not guessed past this point: "Recovery
Confidence" could mean confidence that a SPECIFIC recovery action (from
Aakash's Recovery Strategy Simulator) will succeed, or confidence in the
DIAGNOSIS any recovery decision would be based on. His recovery-action
schema (candidate strategies, expected effects) isn't available here, so
building the former would mean guessing his data shape. Scoped to the
latter: how solid is the anomaly/classification/root-cause diagnosis
behind whatever target gets picked for recovery. His Decision Engine can
combine this with his own cost/risk dimensions -- per his own status
update, "other cost dimensions beyond topology cost need to feed into the
final pick" is still open on his side. Confirm with him whether this is
the right half to own, or whether he actually needs per-strategy
confidence instead -- that would be a different, larger feature reading
his action catalog rather than this one.

Recommendation: never recommend recovering a SYMPTOM directly -- points at
the actual root cause instead, since fixing a symptom node/link won't fix
what's actually wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.network.models import Topology


@dataclass
class RecoveryConfidenceResult:
    target_id: str
    target_type: str
    recovery_confidence: float
    detection_confidence: float
    classification_confidence: float
    is_root_cause: bool
    recommendation: str
    points_to: Optional[str]
    explanation: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class RecoveryConfidenceEngine:
    def evaluate(
        self,
        node_anomaly_results: list,
        link_anomaly_results: list,
        topology: Topology,
        central_node_id: str,
    ) -> list:
        node_class = {c["node_id"]: c for c in classify_failures(node_anomaly_results)}
        link_class = {c["link_id"]: c for c in classify_link_failures(link_anomaly_results)}
        node_det = {r["node_id"]: r for r in node_anomaly_results}
        link_det = {r["link_id"]: r for r in link_anomaly_results}

        rca = analyze_root_causes(node_anomaly_results, link_anomaly_results, topology, central_node_id)
        symptom_of = {}
        root_cause_ids = set()
        for cluster in rca:
            root_cause_ids.add(cluster["root_cause_id"])
            for nid in cluster["affected_nodes"]:
                symptom_of[nid] = cluster["root_cause_id"]
            for lid in cluster["affected_links"]:
                symptom_of[lid] = cluster["root_cause_id"]

        results = []
        for node_id, cls in node_class.items():
            results.append(
                self._evaluate_one(
                    node_id,
                    "node",
                    cls,
                    node_det[node_id]["score"],
                    node_id in root_cause_ids,
                    symptom_of.get(node_id),
                )
            )
        for link_id, cls in link_class.items():
            results.append(
                self._evaluate_one(
                    link_id,
                    "link",
                    cls,
                    link_det[link_id]["score"],
                    link_id in root_cause_ids,
                    symptom_of.get(link_id),
                )
            )
        return results

    def _evaluate_one(self, target_id, target_type, cls, detection_score, is_root_cause, symptom_of):
        if cls["category"] == "none":
            return RecoveryConfidenceResult(
                target_id=target_id,
                target_type=target_type,
                recovery_confidence=1.0,
                detection_confidence=0.0,
                classification_confidence=0.0,
                is_root_cause=False,
                recommendation="no_action_needed",
                points_to=None,
                explanation=f"{target_id} is healthy -- nothing to recover.",
            )

        if symptom_of:
            return RecoveryConfidenceResult(
                target_id=target_id,
                target_type=target_type,
                recovery_confidence=0.15,
                detection_confidence=round(detection_score, 3),
                classification_confidence=cls["confidence"],
                is_root_cause=False,
                recommendation="act_on_root_cause_instead",
                points_to=symptom_of,
                explanation=(
                    f"{target_id} is a downstream symptom of {symptom_of}. Recovering "
                    f"{target_id} directly won't fix the underlying problem -- low "
                    f"confidence recommended for acting here."
                ),
            )

        security_penalty = 0.0 if cls["possible_security"] else 1.0
        confidence = round(0.5 * detection_score + 0.3 * cls["confidence"] + 0.2 * security_penalty, 3)

        if confidence >= 0.7:
            recommendation = "act_here"
        elif confidence >= 0.4:
            recommendation = "act_with_caution"
        else:
            recommendation = "insufficient_confidence_wait"

        explanation = (
            f"{target_id} classified as {cls['category']} with detection score "
            f"{detection_score:.2f} and classification confidence {cls['confidence']:.2f}."
        )
        if cls["possible_security"]:
            explanation += " Pattern is ambiguous (possible security angle) -- confidence reduced."

        return RecoveryConfidenceResult(
            target_id=target_id,
            target_type=target_type,
            recovery_confidence=confidence,
            detection_confidence=round(detection_score, 3),
            classification_confidence=cls["confidence"],
            is_root_cause=is_root_cause,
            recommendation=recommendation,
            points_to=None,
            explanation=explanation,
        )


def evaluate_recovery_confidence(
    node_anomaly_results: list,
    link_anomaly_results: list,
    topology: Topology,
    central_node_id: str,
    engine: Optional[RecoveryConfidenceEngine] = None,
) -> list:
    """Convenience entry point. Returns JSON-able list[dict]."""
    engine = engine or RecoveryConfidenceEngine()
    return [
        r.to_dict()
        for r in engine.evaluate(node_anomaly_results, link_anomaly_results, topology, central_node_id)
    ]