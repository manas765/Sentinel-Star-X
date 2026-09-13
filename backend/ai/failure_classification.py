
"""
backend/ai/failure_classification.py

Feature 3/16 (global #8): Failure Classification.

REWRITTEN for the real schema (v2). Reason strings changed since Feature 1
checks different fields now (cpu_util_pct/mem_util_pct/jitter_ms/
error_rate_pct instead of bandwidth_mbps/traffic_mbps), and there's a new
link-side classifier since Feature 1 now has a separate LinkAnomalyDetector.

INTERFACE FLAG -- coordinate with Manas, not guessed past this point:
This classifies failure TYPE. It does NOT decide failure vs. security
incident -- that's Manas's differentiation feature. possible_security=True
means "anomalous but doesn't match a known failure signature," for him to
review. Still assuming his differentiator runs in parallel rather than
gating this, per the original flag -- unconfirmed, raise with him.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FailureCategory(str, Enum):
    NODE_DOWN = "node_down"
    NODE_OVERLOAD = "node_overload"
    LATENCY_DEGRADATION = "latency_degradation"
    PACKET_LOSS = "packet_loss"
    LINK_DOWN = "link_down"
    LINK_CONGESTION = "link_congestion"
    UNKNOWN = "unknown"
    NONE = "none"


@dataclass
class ClassificationResult:
    node_id: str
    category: FailureCategory
    confidence: float
    possible_security: bool
    contributing_reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["category"] = self.category.value
        return d


@dataclass
class LinkClassificationResult:
    link_id: str
    category: FailureCategory
    confidence: float
    possible_security: bool
    contributing_reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["category"] = self.category.value
        return d


def _extract(result, *names):
    """Works whether result is a dataclass instance or a dict."""
    out = []
    for name in names:
        out.append(result[name] if isinstance(result, dict) else getattr(result, name))
    return out


class RuleBasedFailureClassifier:
    """v1: rule-based, reading Feature 1's already-tagged reasons."""

    def classify(self, anomaly_results: list) -> list:
        return [self._classify_node(r) for r in anomaly_results]

    def classify_links(self, link_anomaly_results: list) -> list:
        return [self._classify_link(r) for r in link_anomaly_results]

    def _classify_node(self, result) -> ClassificationResult:
        node_id, is_anomalous, score, reasons = _extract(
            result, "node_id", "is_anomalous", "score", "reasons"
        )

        if not is_anomalous:
            return ClassificationResult(
                node_id=node_id,
                category=FailureCategory.NONE,
                confidence=1.0,
                possible_security=False,
                contributing_reasons=[],
            )

        has_down = any(r == "status=down" for r in reasons)
        has_cpu_mem = any(r.startswith("cpu_util_pct") or r.startswith("mem_util_pct") for r in reasons)
        has_loss_or_error = any(
            r.startswith("packet_loss_pct") or r.startswith("error_rate_pct") for r in reasons
        )
        has_latency_or_jitter = any(
            r.startswith("latency_ms") or r.startswith("jitter_ms") for r in reasons
        )

        if has_down:
            category = FailureCategory.NODE_DOWN
        elif has_cpu_mem:
            category = FailureCategory.NODE_OVERLOAD
        elif has_loss_or_error:
            category = FailureCategory.PACKET_LOSS
        elif has_latency_or_jitter:
            category = FailureCategory.LATENCY_DEGRADATION
        else:
            category = FailureCategory.UNKNOWN

        return ClassificationResult(
            node_id=node_id,
            category=category,
            confidence=round(score, 3),
            possible_security=(category == FailureCategory.UNKNOWN),
            contributing_reasons=list(reasons),
        )

    def _classify_link(self, result) -> LinkClassificationResult:
        link_id, is_anomalous, score, reasons = _extract(
            result, "link_id", "is_anomalous", "score", "reasons"
        )

        if not is_anomalous:
            return LinkClassificationResult(
                link_id=link_id,
                category=FailureCategory.NONE,
                confidence=1.0,
                possible_security=False,
                contributing_reasons=[],
            )

        has_down = any(r == "status=down" for r in reasons)
        has_utilization = any(r.startswith("utilization_pct") for r in reasons)

        if has_down:
            category = FailureCategory.LINK_DOWN
        elif has_utilization:
            category = FailureCategory.LINK_CONGESTION
        else:
            category = FailureCategory.UNKNOWN

        return LinkClassificationResult(
            link_id=link_id,
            category=category,
            confidence=round(score, 3),
            possible_security=(category == FailureCategory.UNKNOWN),
            contributing_reasons=list(reasons),
        )


FailureClassifier = RuleBasedFailureClassifier


def classify_failures(anomaly_results: list, classifier: Optional[RuleBasedFailureClassifier] = None) -> list:
    classifier = classifier or FailureClassifier()
    return [c.to_dict() for c in classifier.classify(anomaly_results)]


def classify_link_failures(
    link_anomaly_results: list, classifier: Optional[RuleBasedFailureClassifier] = None
) -> list:
    classifier = classifier or FailureClassifier()
    return [c.to_dict() for c in classifier.classify_links(link_anomaly_results)]