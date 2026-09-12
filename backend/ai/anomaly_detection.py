"""
backend/ai/anomaly_detection.py

Feature 1/16 (global #6): AI Anomaly Detection.

Approach: hybrid, per your call.
  v1 (this file) — threshold-based detector: fast, deterministic, explainable,
  works from the very first snapshot with no training data required.
  v2 (later) — a trained-model detector (e.g. isolation forest) plugs into
  the same BaseAnomalyDetector interface below, so no caller has to change
  when it lands.

Input contract
--------------
Takes a "snapshot": a list of per-node telemetry dicts, the same shape
produced by telemetry_sim.SyntheticTelemetryGenerator.generate_snapshot().
That schema is still an ASSUMPTION pending Akshata confirming her real
field names (see telemetry_sim.py) — when they land, only field-name
lookups below need to change, not the detection logic.

NOT YET WIRED: an HTTP endpoint. Definition-of-done calls for one, but the
project docs don't say which web framework the team's using (Flask/FastAPI/
etc. isn't specified anywhere). detect_anomalies() below returns plain
JSON-able dicts, so wiring a route is a few lines once that's settled —
flagging this rather than guessing a framework into the shared repo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyResult:
    node_id: str
    is_anomalous: bool
    score: float  # 0.0 (normal) - 1.0 (severe)
    severity: Severity
    reasons: list = field(default_factory=list)  # human-readable trigger explanations

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["severity"] = self.severity.value
        return d


class BaseAnomalyDetector(ABC):
    """Common interface so the threshold detector and a future model-based
    detector are interchangeable to every caller (Root Cause Analysis,
    Predictive Failure Detection, the dashboard, etc.)."""

    @abstractmethod
    def detect(self, snapshot: list) -> list:
        """snapshot: list of node telemetry dicts. Returns list[AnomalyResult]."""
        raise NotImplementedError


@dataclass
class ThresholdConfig:
    """
    Per-node-type thresholds. Defaults set relative to the synthetic
    generator's baseline ranges (leaf vs central have very different normal
    operating ranges, so they need separate thresholds). Retune once real
    telemetry -- and real baselines -- come in from Akshata.
    """
    leaf_max_latency_ms: float = 60.0
    leaf_max_packet_loss_pct: float = 5.0
    leaf_min_bandwidth_mbps: float = 40.0
    leaf_max_traffic_mbps: float = 80.0

    central_max_latency_ms: float = 15.0
    central_max_packet_loss_pct: float = 5.0
    central_min_bandwidth_mbps: float = 400.0
    central_max_traffic_mbps: float = 500.0


class ThresholdAnomalyDetector(BaseAnomalyDetector):
    """v1: static, per-field thresholds. No training/history required --
    which is what makes it the right 'now' half of the hybrid, while a
    model-based detector (v2) is still future work."""

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def detect(self, snapshot: list) -> list:
        return [self._check_node(node) for node in snapshot]

    def _check_node(self, node: dict) -> AnomalyResult:
        cfg = self.config
        is_central = node.get("is_central", False)
        reasons = []
        metric_scores = []

        status = node.get("status")
        if status == "down":
            reasons.append("status=down")
            metric_scores.append(1.0)
        elif status == "degraded":
            reasons.append("status=degraded")
            metric_scores.append(0.5)

        max_latency = cfg.central_max_latency_ms if is_central else cfg.leaf_max_latency_ms
        latency = node.get("latency_ms", 0.0)
        if latency > max_latency:
            reasons.append(f"latency_ms={latency} > {max_latency}")
            metric_scores.append(min(latency / max_latency / 3, 1.0))

        max_loss = cfg.central_max_packet_loss_pct if is_central else cfg.leaf_max_packet_loss_pct
        loss = node.get("packet_loss_pct", 0.0)
        if loss > max_loss:
            reasons.append(f"packet_loss_pct={loss} > {max_loss}")
            metric_scores.append(min(loss / max_loss / 3, 1.0))

        min_bw = cfg.central_min_bandwidth_mbps if is_central else cfg.leaf_min_bandwidth_mbps
        bw = node.get("bandwidth_mbps", min_bw)
        if bw < min_bw:
            reasons.append(f"bandwidth_mbps={bw} < {min_bw}")
            metric_scores.append(min((min_bw - bw) / min_bw, 1.0))

        max_traffic = cfg.central_max_traffic_mbps if is_central else cfg.leaf_max_traffic_mbps
        traffic = max(node.get("traffic_in_mbps", 0.0), node.get("traffic_out_mbps", 0.0))
        if traffic > max_traffic:
            reasons.append(f"traffic_mbps={traffic} > {max_traffic}")
            metric_scores.append(min(traffic / max_traffic / 3, 1.0))

        score = max(metric_scores) if metric_scores else 0.0
        is_anomalous = bool(metric_scores)
        severity = self._score_to_severity(score, is_anomalous)

        return AnomalyResult(
            node_id=node["node_id"],
            is_anomalous=is_anomalous,
            score=round(score, 3),
            severity=severity,
            reasons=reasons,
        )

    @staticmethod
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


# Active detector implementation. Swap this line to plug in a model-based
# detector later (e.g. AnomalyDetector = IsolationForestAnomalyDetector) --
# every caller importing AnomalyDetector from this module is unaffected.
AnomalyDetector = ThresholdAnomalyDetector


def detect_anomalies(snapshot: list, detector: Optional[BaseAnomalyDetector] = None) -> list:
    """Convenience entry point. Returns JSON-able list[dict] -- wrap this
    directly in whichever web framework the team settles on."""
    detector = detector or AnomalyDetector()
    return [r.to_dict() for r in detector.detect(snapshot)]