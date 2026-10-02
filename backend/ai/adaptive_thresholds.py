"""
backend/ai/adaptive_thresholds.py

Feature 15/16 (global #59): Adaptive Threshold Management.

Recalibrates Feature 1's NodeThresholdConfig/LinkThresholdConfig from
OBSERVED data (mean + k*std per metric) instead of the hand-tuned constants
they shipped with -- those were tuned against the synthetic generator's
known ranges, which won't match real telemetry.

Scoped to per-node-TYPE (leaf vs central) rather than per-individual-node,
so the output plugs straight into ThresholdAnomalyDetector / LinkAnomaly-
Detector with zero changes to anomaly_detection.py -- just swap in the
computed config. True per-device thresholds (e.g. a DB server vs an IoT
device having very different normal ranges) would need DeviceType to
actually vary telemetry generation first, which it doesn't yet -- natural
v2 once it does.

Feeds only from ticks Feature 1 itself didn't flag as anomalous, so an
ongoing incident doesn't drag the baseline toward "broken looks normal."
Floors keep thresholds from collapsing to near-zero during a long quiet
period with almost no variance in the data.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from backend.ai.anomaly_detection import LinkThresholdConfig, NodeThresholdConfig
from backend.telemetry.schema import TelemetrySnapshot

SHARED_NODE_METRICS = ["jitter_ms", "packet_loss_pct", "error_rate_pct", "cpu_util_pct", "mem_util_pct"]
LINK_METRICS = ["utilization_pct", "latency_ms", "packet_loss_pct"]

FLOORS = {
    "leaf_latency_ms": 10.0,
    "central_latency_ms": 5.0,
    "jitter_ms": 1.0,
    "packet_loss_pct": 1.0,
    "error_rate_pct": 1.0,
    "cpu_util_pct": 50.0,
    "mem_util_pct": 50.0,
    "link_utilization_pct": 50.0,
    "link_latency_ms": 5.0,
    "link_packet_loss_pct": 1.0,
}


class _RollingStat:
    def __init__(self, window: int = 200):
        self.values: Deque[float] = deque(maxlen=window)

    def add(self, value: float) -> None:
        self.values.append(value)

    @property
    def mean(self) -> float:
        return sum(self.values) / len(self.values) if self.values else 0.0

    @property
    def std(self) -> float:
        n = len(self.values)
        if n < 2:
            return 0.0
        m = self.mean
        return math.sqrt(sum((v - m) ** 2 for v in self.values) / (n - 1))

    def __len__(self):
        return len(self.values)


class AdaptiveThresholdManager:
    def __init__(self, window: int = 200, k: float = 4.0, min_samples: int = 20):
        self.window = window
        self.k = k  # how many std deviations above mean counts as anomalous
        self.min_samples = min_samples
        self._leaf_latency = _RollingStat(window)
        self._central_latency = _RollingStat(window)
        self._shared_node_stats = {m: _RollingStat(window) for m in SHARED_NODE_METRICS}
        self._link_stats = {m: _RollingStat(window) for m in LINK_METRICS}

    def update(
        self,
        snapshot: TelemetrySnapshot,
        node_anomaly_results: list,
        link_anomaly_results: list,
        central_node_id: str,
    ) -> None:
        anomalous_nodes = {r["node_id"] for r in node_anomaly_results if r["is_anomalous"]}
        anomalous_links = {r["link_id"] for r in link_anomaly_results if r["is_anomalous"]}

        for node in snapshot.nodes:
            if node.node_id in anomalous_nodes:
                continue
            if node.node_id == central_node_id:
                self._central_latency.add(node.latency_ms)
            else:
                self._leaf_latency.add(node.latency_ms)
            for metric in SHARED_NODE_METRICS:
                self._shared_node_stats[metric].add(getattr(node, metric))

        for link in snapshot.links:
            if link.link_id in anomalous_links:
                continue
            for metric in LINK_METRICS:
                self._link_stats[metric].add(getattr(link, metric))

    def ready(self) -> bool:
        return (
            len(self._leaf_latency) >= self.min_samples
            and len(self._central_latency) >= self.min_samples
            and len(self._link_stats["latency_ms"]) >= self.min_samples
        )

    def _threshold(self, stat: _RollingStat, floor: float) -> float:
        if len(stat) < self.min_samples:
            return floor
        return max(stat.mean + self.k * stat.std, floor)

    def get_node_threshold_config(self) -> NodeThresholdConfig:
        shared = {m: self._threshold(self._shared_node_stats[m], FLOORS[m]) for m in SHARED_NODE_METRICS}
        return NodeThresholdConfig(
            leaf_max_latency_ms=round(self._threshold(self._leaf_latency, FLOORS["leaf_latency_ms"]), 2),
            central_max_latency_ms=round(self._threshold(self._central_latency, FLOORS["central_latency_ms"]), 2),
            max_jitter_ms=round(shared["jitter_ms"], 2),
            max_packet_loss_pct=round(shared["packet_loss_pct"], 2),
            max_error_rate_pct=round(shared["error_rate_pct"], 2),
            max_cpu_util_pct=round(shared["cpu_util_pct"], 2),
            max_mem_util_pct=round(shared["mem_util_pct"], 2),
        )

    def get_link_threshold_config(self) -> LinkThresholdConfig:
        return LinkThresholdConfig(
            max_utilization_pct=round(
                self._threshold(self._link_stats["utilization_pct"], FLOORS["link_utilization_pct"]), 2
            ),
            max_latency_ms=round(self._threshold(self._link_stats["latency_ms"], FLOORS["link_latency_ms"]), 2),
            max_packet_loss_pct=round(
                self._threshold(self._link_stats["packet_loss_pct"], FLOORS["link_packet_loss_pct"]), 2
            ),
        )