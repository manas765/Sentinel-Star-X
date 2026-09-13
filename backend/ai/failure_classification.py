"""
backend/ai/failure_classification.py

Feature 3/16 (global #8): Failure Classification.

Classifies WHAT KIND of failure a node is experiencing, using the reasons
Feature 1's AnomalyDetector already attaches to each result (each reason
already names the metric that tripped, e.g. "latency_ms=85 > 60") -- so
this is a rule-based mapping on top of Feature 1's output, not a second
detector duplicating its work.

INTERFACE FLAG -- coordinate with Manas, not guessed past this point:
This classifies failure TYPE (node down / latency / packet loss /
congestion / central overload). It does NOT decide failure vs. security
incident -- that's Manas's "Failure vs Security Incident Differentiation"
feature, and the roadmap explicitly calls out these two need to line up so
we're not building two competing classifiers. Two reasonable ways to wire
them together, needs his input on which:
  (a) his differentiator runs first and only routes confirmed non-security
      failures to this classifier, or
  (b) this always runs, and just tags a possible_security flag whenever the
      pattern doesn't match a clean known failure signature, for him to
      review.
Built assuming (b) for now since it's the more standalone-testable choice,
not because it's confirmed correct -- raise this with him before relying on
possible_security for anything real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FailureCategory(str, Enum):
    NODE_DOWN = "node_down"
    LATENCY_DEGRADATION = "latency_degradation"
    PACKET_LOSS = "packet_loss"
    CONGESTION = "congestion"
    CENTRAL_OVERLOAD = "central_overload"
    UNKNOWN = "unknown"  # anomalous but no clean metric pattern -- see interface flag above
    NONE = "none"  # not anomalous


@dataclass
class ClassificationResult:
    node_id: str
    category: FailureCategory
    confidence: float  # 0.0 - 1.0
    possible_security: bool  # True when the pattern doesn't match a known failure signature
    contributing_reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["category"] = self.category.value
        return d


class BaseFailureClassifier:
    def classify(self, anomaly_results: list) -> list:
        raise NotImplementedError


class RuleBasedFailureClassifier(BaseFailureClassifier):
    """v1: rule-based, reading Feature 1's already-tagged reasons. No
    training data needed, and every rule traces back to a specific metric,
    which keeps it aligned with the later Explainable AI feature."""

    def classify(self, anomaly_results: list) -> list:
        return [self._classify_one(r) for r in anomaly_results]

    def _classify_one(self, result) -> ClassificationResult:
        # Accepts either AnomalyResult objects or dicts (e.g. straight
        # from detect_anomalies()).
        reasons = result.reasons if hasattr(result, "reasons") else result.get("reasons", [])
        node_id = result.node_id if hasattr(result, "node_id") else result["node_id"]
        is_anomalous = (
            result.is_anomalous if hasattr(result, "is_anomalous") else result["is_anomalous"]
        )
        score = result.score if hasattr(result, "score") else result["score"]

        if not is_anomalous:
            return ClassificationResult(
                node_id=node_id,
                category=FailureCategory.NONE,
                confidence=1.0,
                possible_security=False,
                contributing_reasons=[],
            )

        has_down = any(r == "status=down" for r in reasons)
        has_bandwidth = any(r.startswith("bandwidth_mbps") for r in reasons)
        has_traffic = any(r.startswith("traffic_mbps") for r in reasons)
        has_latency = any(r.startswith("latency_ms") for r in reasons)
        has_loss = any(r.startswith("packet_loss_pct") for r in reasons)

        if has_down:
            category = FailureCategory.NODE_DOWN
        elif has_bandwidth or has_traffic:
            category = FailureCategory.CONGESTION
        elif has_latency and has_loss:
            category = FailureCategory.CENTRAL_OVERLOAD
        elif has_loss:
            category = FailureCategory.PACKET_LOSS
        elif has_latency:
            category = FailureCategory.LATENCY_DEGRADATION
        else:
            category = FailureCategory.UNKNOWN

        possible_security = category == FailureCategory.UNKNOWN

        return ClassificationResult(
            node_id=node_id,
            category=category,
            confidence=round(score, 3),
            possible_security=possible_security,
            contributing_reasons=list(reasons),
        )


FailureClassifier = RuleBasedFailureClassifier


def classify_failures(
    anomaly_results: list, classifier: Optional[BaseFailureClassifier] = None
) -> list:
    """Convenience entry point. Accepts either AnomalyResult objects or
    dicts. Returns JSON-able list[dict]."""
    classifier = classifier or FailureClassifier()
    return [c.to_dict() for c in classifier.classify(anomaly_results)]