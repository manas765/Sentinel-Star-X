"""
backend/ai/explainable_ai.py

Feature 8/16 (global #37): Explainable AI.

Turns the raw, already-technical outputs of Features 1 (anomaly detection),
3 (classification), and 4 (root cause) into a single human-readable
explanation per node/link -- something a dashboard panel or an ops person
without ML background can read directly, instead of raw threshold reason
strings like "latency_ms=85.3 > 60".

Not a new detection layer -- purely synthesizes what earlier features
already computed. Uses root cause clusters to distinguish "here's why THIS
is broken" from "here's why it's broken, and it's actually downstream of
something else" -- that distinction is the main value-add over just
reading Feature 3's output directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.network.models import Topology

CATEGORY_PHRASING = {
    "node_down": "is completely unreachable",
    "node_overload": "is under heavy resource load (CPU/memory)",
    "latency_degradation": "is responding much slower than usual",
    "packet_loss": "is dropping/erroring on a significant share of packets",
    "link_down": "is completely down",
    "link_congestion": "is saturated (utilization over capacity)",
    "unknown": "is showing abnormal behavior that doesn't match a known failure pattern",
    "none": "is healthy",
}

SEVERITY_PHRASING = {
    "none": "no concern",
    "low": "minor",
    "medium": "moderate",
    "high": "serious",
    "critical": "critical",
}


@dataclass
class Explanation:
    target_id: str
    target_type: str  # "node" | "link"
    summary: str
    details: list = field(default_factory=list)
    confidence: float = 0.0
    is_root_cause: bool = False
    is_symptom_of: Optional[str] = None
    possible_security: bool = False

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class ExplainableAIEngine:
    def explain(
        self,
        node_anomaly_results: list,
        link_anomaly_results: list,
        topology: Topology,
        central_node_id: str,
    ) -> list:
        node_class = {c["node_id"]: c for c in classify_failures(node_anomaly_results)}
        link_class = {c["link_id"]: c for c in classify_link_failures(link_anomaly_results)}
        node_severity = {r["node_id"]: r["severity"] for r in node_anomaly_results}
        link_severity = {r["link_id"]: r["severity"] for r in link_anomaly_results}

        rca = analyze_root_causes(node_anomaly_results, link_anomaly_results, topology, central_node_id)
        symptom_of = {}
        root_cause_ids = set()
        for cluster in rca:
            root_cause_ids.add(cluster["root_cause_id"])
            for nid in cluster["affected_nodes"]:
                symptom_of[nid] = cluster["root_cause_id"]
            for lid in cluster["affected_links"]:
                symptom_of[lid] = cluster["root_cause_id"]

        explanations = []
        for node_id, cls in node_class.items():
            explanations.append(
                self._build(
                    target_id=node_id,
                    target_type="node",
                    cls=cls,
                    severity=node_severity.get(node_id, "none"),
                    is_root_cause=(node_id in root_cause_ids),
                    is_symptom_of=symptom_of.get(node_id),
                )
            )
        for link_id, cls in link_class.items():
            explanations.append(
                self._build(
                    target_id=link_id,
                    target_type="link",
                    cls=cls,
                    severity=link_severity.get(link_id, "none"),
                    is_root_cause=(link_id in root_cause_ids),
                    is_symptom_of=symptom_of.get(link_id),
                )
            )
        return explanations

    def _build(self, target_id, target_type, cls, severity, is_root_cause, is_symptom_of) -> Explanation:
        category = cls["category"]
        phrase = CATEGORY_PHRASING.get(category, CATEGORY_PHRASING["unknown"])
        details = []

        if category == "none":
            summary = f"{target_id} {phrase}."
        else:
            severity_word = SEVERITY_PHRASING.get(severity, "moderate")
            summary = f"{target_id} {phrase} ({severity_word} severity)."
            details.append(f"Classified as: {category}")
            details.append(f"Confidence: {cls['confidence']}")
            if cls["contributing_reasons"]:
                details.append("Based on: " + "; ".join(cls["contributing_reasons"]))

            if is_symptom_of:
                details.append(
                    f"This appears to be a downstream symptom of {is_symptom_of}, not an independent problem."
                )
            elif is_root_cause:
                details.append("This appears to be an independent root cause, not a symptom of something else.")

            if cls["possible_security"]:
                details.append(
                    "Pattern doesn't match a known failure signature -- flagged for security review "
                    "(see failure_classification.py's interface note re: Manas's differentiator)."
                )

        return Explanation(
            target_id=target_id,
            target_type=target_type,
            summary=summary,
            details=details,
            confidence=cls["confidence"],
            is_root_cause=is_root_cause,
            is_symptom_of=is_symptom_of,
            possible_security=cls["possible_security"],
        )


def explain_network_state(
    node_anomaly_results: list,
    link_anomaly_results: list,
    topology: Topology,
    central_node_id: str,
    engine: Optional[ExplainableAIEngine] = None,
) -> list:
    """Convenience entry point. Returns JSON-able list[dict]."""
    engine = engine or ExplainableAIEngine()
    return [
        e.to_dict()
        for e in engine.explain(node_anomaly_results, link_anomaly_results, topology, central_node_id)
    ]