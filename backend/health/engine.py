"""
backend/health/engine.py

Network Health Engine (feature 6.3).

Computes a dynamic 0-100 health score per node from telemetry. Score
incorporates: resource utilization, connectivity, packet loss, latency,
errors, traffic, and historical behavior (via EMA smoothing + a volatility
penalty). Predicted failure risk is an OPTIONAL external input - that
model lives with the AI/Prediction track, not here; this engine just has
a slot for it (defaults to 0 until that track wires it in).

Typical use:

    engine = HealthEngine()
    for node in snapshot.nodes:
        score = engine.score_node(node)
        twin.attach_health_score(node.node_id, score)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from backend.telemetry.schema import NodeStatus, NodeTelemetry

# Thresholds: values at/above these are treated as "fully bad" for that
# dimension (100% penalty). Tune these once real traffic patterns are
# observed - these are reasonable starting points, not measured constants.
_CPU_BAD = 90.0
_MEM_BAD = 90.0
_LATENCY_BAD_MS = 100.0
_PACKET_LOSS_BAD_PCT = 10.0
_ERROR_RATE_BAD_PCT = 5.0
_JITTER_BAD_MS = 20.0

# How much each dimension contributes to the raw score (must sum to 1.0)
_WEIGHTS = {
    "cpu": 0.15,
    "mem": 0.10,
    "latency": 0.20,
    "packet_loss": 0.20,
    "error_rate": 0.15,
    "jitter": 0.10,
    "connectivity": 0.10,  # binary: down = 0, up/degraded = based on status
}

_HISTORY_LEN = 20
_EMA_ALPHA = 0.3  # weight on the newest raw score vs prior smoothed score


def _penalty(value: float, bad_at: float) -> float:
    """0.0 (no penalty) to 1.0 (full penalty), linear up to bad_at."""
    return max(0.0, min(1.0, value / bad_at))


@dataclass
class _NodeHistory:
    smoothed_score: float = 100.0
    raw_scores: deque = None

    def __post_init__(self):
        if self.raw_scores is None:
            self.raw_scores = deque(maxlen=_HISTORY_LEN)


class HealthEngine:
    def __init__(self):
        self._history: dict[str, _NodeHistory] = {}

    def score_node(self, telemetry: NodeTelemetry, predicted_failure_risk: float = 0.0) -> float:
        """
        predicted_failure_risk: optional, 0.0-1.0, supplied by the AI
        track's failure prediction model (feature 6.7). Defaults to 0
        until that model exists / is wired in.
        """
        history = self._history.setdefault(telemetry.node_id, _NodeHistory())

        if telemetry.status == NodeStatus.DOWN:
            raw_score = 0.0
        else:
            connectivity_penalty = 0.4 if telemetry.status == NodeStatus.DEGRADED else 0.0
            total_penalty = (
                _WEIGHTS["cpu"] * _penalty(telemetry.cpu_util_pct, _CPU_BAD)
                + _WEIGHTS["mem"] * _penalty(telemetry.mem_util_pct, _MEM_BAD)
                + _WEIGHTS["latency"] * _penalty(telemetry.latency_ms, _LATENCY_BAD_MS)
                + _WEIGHTS["packet_loss"] * _penalty(telemetry.packet_loss_pct, _PACKET_LOSS_BAD_PCT)
                + _WEIGHTS["error_rate"] * _penalty(telemetry.error_rate_pct, _ERROR_RATE_BAD_PCT)
                + _WEIGHTS["jitter"] * _penalty(telemetry.jitter_ms, _JITTER_BAD_MS)
                + _WEIGHTS["connectivity"] * connectivity_penalty
            )
            raw_score = 100.0 * (1.0 - total_penalty)
            raw_score = raw_score * (1.0 - min(1.0, max(0.0, predicted_failure_risk)) * 0.3)

        history.raw_scores.append(raw_score)

        # Historical behavior: smooth via EMA so one noisy tick doesn't
        # whiplash the score, and add a small volatility penalty if the
        # node's recent scores have been swinging a lot (unstable node).
        history.smoothed_score = (
            _EMA_ALPHA * raw_score + (1 - _EMA_ALPHA) * history.smoothed_score
        )
        volatility_penalty = 0.0
        if len(history.raw_scores) >= 3:
            recent = list(history.raw_scores)[-5:]
            spread = max(recent) - min(recent)
            volatility_penalty = min(10.0, spread * 0.1)

        final_score = max(0.0, min(100.0, history.smoothed_score - volatility_penalty))
        return round(final_score, 2)

    def score_snapshot(self, nodes: list, risk_by_node: dict | None = None) -> dict:
        """Convenience: score every node in a snapshot at once.
        risk_by_node: optional {node_id: predicted_failure_risk}."""
        risk_by_node = risk_by_node or {}
        return {
            n.node_id: self.score_node(n, predicted_failure_risk=risk_by_node.get(n.node_id, 0.0))
            for n in nodes
        }
