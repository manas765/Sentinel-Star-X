"""
backend/ai/anomaly_detection.py

Feature 1/16 (global #6): AI Anomaly Detection.

REWRITTEN against the real schema (v2). Key changes from v1:
- Node checks no longer touch bandwidth/traffic thresholds for "congestion"
  -- that concept moved to the link level (utilization_pct), which is a
  cleaner signal than inferring congestion from a node's own throughput.
- is_central is no longer on the telemetry object. detect() now takes a
  central_node_id so it knows which thresholds to apply per node.
- New node metrics (cpu_util_pct, mem_util_pct, jitter_ms, error_rate_pct)
  are checked.
- A second detector, LinkAnomalyDetector, checks link telemetry
  independently -- this is what lets us tell "the node died" apart from
  "the link to it died," which was the whole point of the schema split.

Still hybrid per your call: threshold-based now, both detectors share the
BaseAnomalyDetector-style interface so a trained model can slot in later
without callers changing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.telemetry.schema import LinkStatus, LinkTelemetry, NodeStatus, NodeTelemetry, TelemetrySnapshot


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _score_to_severity(score: float, is_anomalous: bool) -> Severity:
    if not is_anomalous:
        return Severity.NONE
    if score >= 0.85:
        return Severity.CRITICAL
    if score >= 0.6:
        return Severity.HIGH
    if score >= 0.3:
        return Severity.MEDIUM
    return Severity.LOW


@dataclass
class AnomalyResult:
    node_id: str
    is_anomalous: bool
    score: float  # 0.0 (normal) - 1.0 (severe)
    severity: Severity
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["severity"] = self.severity.value
        return d


@dataclass
class LinkAnomalyResult:
    link_id: str
    is_anomalous: bool
    score: float
    severity: Severity
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["severity"] = self.severity.value
        return d


class BaseAnomalyDetector(ABC):
    """Common interface so the threshold detector and a future model-based
    detector are interchangeable to every caller."""

    @abstractmethod
    def detect(self, snapshot: TelemetrySnapshot, central_node_id: Optional[str] = None) -> list:
        raise NotImplementedError


@dataclass
class NodeThresholdConfig:
    """Retune once real telemetry (and real baselines) come in."""
    leaf_max_latency_ms: float = 60.0
    central_max_latency_ms: float = 15.0
    max_jitter_ms: float = 5.0
    max_packet_loss_pct: float = 5.0
    max_error_rate_pct: float = 5.0
    max_cpu_util_pct: float = 85.0
    max_mem_util_pct: float = 85.0


class ThresholdAnomalyDetector(BaseAnomalyDetector):
    """v1: static per-field thresholds on node telemetry."""

    def __init__(self, config: Optional[NodeThresholdConfig] = None):
        self.config = config or NodeThresholdConfig()

    def detect(self, snapshot: TelemetrySnapshot, central_node_id: Optional[str] = None) -> list:
        return [
            self._check_node(n, is_central=(n.node_id == central_node_id))
            for n in snapshot.nodes
        ]

    def _check_node(self, node: NodeTelemetry, is_central: bool) -> AnomalyResult:
        cfg = self.config
        reasons = []
        metric_scores = []

        if node.status == NodeStatus.DOWN:
            reasons.append("status=down")
            metric_scores.append(1.0)
        elif node.status == NodeStatus.DEGRADED:
            reasons.append("status=degraded")
            metric_scores.append(0.5)

        max_latency = cfg.central_max_latency_ms if is_central else cfg.leaf_max_latency_ms
        if node.latency_ms > max_latency:
            reasons.append(f"latency_ms={node.latency_ms} > {max_latency}")
            metric_scores.append(min(node.latency_ms / max_latency / 3, 1.0))

        if node.jitter_ms > cfg.max_jitter_ms:
            reasons.append(f"jitter_ms={node.jitter_ms} > {cfg.max_jitter_ms}")
            metric_scores.append(min(node.jitter_ms / cfg.max_jitter_ms / 3, 1.0))

        if node.packet_loss_pct > cfg.max_packet_loss_pct:
            reasons.append(f"packet_loss_pct={node.packet_loss_pct} > {cfg.max_packet_loss_pct}")
            metric_scores.append(min(node.packet_loss_pct / cfg.max_packet_loss_pct / 3, 1.0))

        if node.error_rate_pct > cfg.max_error_rate_pct:
            reasons.append(f"error_rate_pct={node.error_rate_pct} > {cfg.max_error_rate_pct}")
            metric_scores.append(min(node.error_rate_pct / cfg.max_error_rate_pct / 3, 1.0))

        if node.cpu_util_pct > cfg.max_cpu_util_pct:
            reasons.append(f"cpu_util_pct={node.cpu_util_pct} > {cfg.max_cpu_util_pct}")
            metric_scores.append(min(node.cpu_util_pct / cfg.max_cpu_util_pct / 3, 1.0))

        if node.mem_util_pct > cfg.max_mem_util_pct:
            reasons.append(f"mem_util_pct={node.mem_util_pct} > {cfg.max_mem_util_pct}")
            metric_scores.append(min(node.mem_util_pct / cfg.max_mem_util_pct / 3, 1.0))

        score = max(metric_scores) if metric_scores else 0.0
        is_anomalous = bool(metric_scores)
        return AnomalyResult(
            node_id=node.node_id,
            is_anomalous=is_anomalous,
            score=round(score, 3),
            severity=_score_to_severity(score, is_anomalous),
            reasons=reasons,
        )


@dataclass
class LinkThresholdConfig:
    max_utilization_pct: float = 85.0
    max_latency_ms: float = 20.0
    max_packet_loss_pct: float = 5.0


class LinkAnomalyDetector:
    """NEW in v2 -- checks link telemetry independently of node telemetry,
    so a link can be flagged as failing/congested even if both nodes on
    either end of it report perfectly healthy telemetry."""

    def __init__(self, config: Optional[LinkThresholdConfig] = None):
        self.config = config or LinkThresholdConfig()

    def detect(self, snapshot: TelemetrySnapshot) -> list:
        return [self._check_link(l) for l in snapshot.links]

    def _check_link(self, link: LinkTelemetry) -> LinkAnomalyResult:
        cfg = self.config
        reasons = []
        metric_scores = []

        if link.status == LinkStatus.DOWN:
            reasons.append("status=down")
            metric_scores.append(1.0)
        elif link.status == LinkStatus.DEGRADED:
            reasons.append("status=degraded")
            metric_scores.append(0.5)

        if link.utilization_pct > cfg.max_utilization_pct:
            reasons.append(f"utilization_pct={link.utilization_pct} > {cfg.max_utilization_pct}")
            metric_scores.append(min(link.utilization_pct / cfg.max_utilization_pct / 1.5, 1.0))

        if link.latency_ms > cfg.max_latency_ms:
            reasons.append(f"latency_ms={link.latency_ms} > {cfg.max_latency_ms}")
            metric_scores.append(min(link.latency_ms / cfg.max_latency_ms / 3, 1.0))

        if link.packet_loss_pct > cfg.max_packet_loss_pct:
            reasons.append(f"packet_loss_pct={link.packet_loss_pct} > {cfg.max_packet_loss_pct}")
            metric_scores.append(min(link.packet_loss_pct / cfg.max_packet_loss_pct / 3, 1.0))

        score = max(metric_scores) if metric_scores else 0.0
        is_anomalous = bool(metric_scores)
        return LinkAnomalyResult(
            link_id=link.link_id,
            is_anomalous=is_anomalous,
            score=round(score, 3),
            severity=_score_to_severity(score, is_anomalous),
            reasons=reasons,
        )


# Active implementations. Swap these lines to plug in model-based detectors
# later -- callers importing these names are unaffected.
AnomalyDetector = ThresholdAnomalyDetector


def detect_anomalies(
    snapshot: TelemetrySnapshot,
    central_node_id: Optional[str] = None,
    detector: Optional[BaseAnomalyDetector] = None,
) -> list:
    """Node-level anomalies. Returns JSON-able list[dict]."""
    detector = detector or AnomalyDetector()
    return [r.to_dict() for r in detector.detect(snapshot, central_node_id=central_node_id)]


def detect_link_anomalies(
    snapshot: TelemetrySnapshot, detector: Optional[LinkAnomalyDetector] = None
) -> list:
    """Link-level anomalies. Returns JSON-able list[dict]."""
    detector = detector or LinkAnomalyDetector()
    return [r.to_dict() for r in detector.detect(snapshot)]