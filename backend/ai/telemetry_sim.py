"""
backend/ai/telemetry_sim.py

Synthetic telemetry generator — Phase 0 scaffolding for the AI + Prediction track.

Why this exists
----------------
Akshata's Digital Twin is the real source of telemetry, but that feed isn't
wired up yet. This generator produces telemetry shaped like what the project
docs describe (node/link state, traffic, latency, packet loss, bandwidth) so
Phase 1 detection/prediction code can be built and tested against something
concrete right now, without blocking on her track.

ASSUMPTION TO CONFIRM WITH AKSHATA:
The schema in NodeTelemetry below is a guess based on the field list in the
roadmap doc, not her actual output format. Once she shares the real contract,
update this file's schema to match (or replace this generator's output
mapping) rather than changing every Phase 1 module downstream.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeStatus(str, Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


class AnomalyType(str, Enum):
    NODE_DOWN = "node_down"
    LATENCY_SPIKE = "latency_spike"
    PACKET_LOSS = "packet_loss"
    CONGESTION = "congestion"
    CENTRAL_OVERLOAD = "central_overload"


@dataclass
class NodeTelemetry:
    timestamp: float
    node_id: str
    is_central: bool
    status: NodeStatus
    latency_ms: float
    packet_loss_pct: float
    bandwidth_mbps: float
    traffic_in_mbps: float
    traffic_out_mbps: float
    neighbors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["status"] = self.status.value
        return d


class SyntheticTelemetryGenerator:
    """
    Simulates telemetry for a star topology: one central node + N leaf nodes.

    Usage:
        gen = SyntheticTelemetryGenerator(num_leaves=8, seed=42)
        snapshot = gen.generate_snapshot()
        snapshot = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN,
                                          anomaly_node="leaf-3")
        for snap in gen.stream(ticks=100, anomaly_at=50,
                                anomaly=AnomalyType.LATENCY_SPIKE):
            ...
    """

    def __init__(self, num_leaves: int = 8, seed: Optional[int] = None):
        self.num_leaves = num_leaves
        self.central_id = "central"
        self.leaf_ids = [f"leaf-{i}" for i in range(num_leaves)]
        self._rng = random.Random(seed)

    def _baseline_node(self, node_id: str, is_central: bool, ts: float) -> NodeTelemetry:
        neighbors = list(self.leaf_ids) if is_central else [self.central_id]
        return NodeTelemetry(
            timestamp=ts,
            node_id=node_id,
            is_central=is_central,
            status=NodeStatus.UP,
            latency_ms=round(
                self._rng.uniform(1.0, 5.0) if is_central else self._rng.uniform(5.0, 20.0), 2
            ),
            packet_loss_pct=round(self._rng.uniform(0.0, 0.5), 3),
            bandwidth_mbps=round(
                self._rng.uniform(800, 1000) if is_central else self._rng.uniform(80, 100), 2
            ),
            traffic_in_mbps=round(
                self._rng.uniform(50, 400) if is_central else self._rng.uniform(5, 40), 2
            ),
            traffic_out_mbps=round(
                self._rng.uniform(50, 400) if is_central else self._rng.uniform(5, 40), 2
            ),
            neighbors=neighbors,
        )

    def generate_snapshot(
        self,
        anomaly: Optional[AnomalyType] = None,
        anomaly_node: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> list:
        """Returns a list of node telemetry dicts for one point in time."""
        ts = ts if ts is not None else time.time()
        nodes = [self._baseline_node(self.central_id, True, ts)]
        nodes += [self._baseline_node(nid, False, ts) for nid in self.leaf_ids]

        if anomaly:
            target_id = anomaly_node or self._rng.choice(self.leaf_ids)
            nodes = [
                self._apply_anomaly(n, anomaly) if n.node_id == target_id else n
                for n in nodes
            ]

        return [n.to_dict() for n in nodes]

    def _apply_anomaly(self, node: NodeTelemetry, anomaly: AnomalyType) -> NodeTelemetry:
        if anomaly == AnomalyType.NODE_DOWN:
            node.status = NodeStatus.DOWN
            node.latency_ms = 0.0
            node.packet_loss_pct = 100.0
            node.bandwidth_mbps = 0.0
            node.traffic_in_mbps = 0.0
            node.traffic_out_mbps = 0.0
        elif anomaly == AnomalyType.LATENCY_SPIKE:
            node.status = NodeStatus.DEGRADED
            node.latency_ms *= self._rng.uniform(8, 20)
        elif anomaly == AnomalyType.PACKET_LOSS:
            node.status = NodeStatus.DEGRADED
            node.packet_loss_pct = round(self._rng.uniform(15, 60), 2)
        elif anomaly == AnomalyType.CONGESTION:
            node.status = NodeStatus.DEGRADED
            node.traffic_in_mbps *= self._rng.uniform(3, 6)
            node.traffic_out_mbps *= self._rng.uniform(3, 6)
            node.bandwidth_mbps *= 0.3
        elif anomaly == AnomalyType.CENTRAL_OVERLOAD:
            node.status = NodeStatus.DEGRADED
            node.latency_ms *= self._rng.uniform(5, 10)
            node.packet_loss_pct = round(self._rng.uniform(5, 25), 2)
        return node

    def stream(
        self,
        ticks: int = 50,
        interval_s: float = 1.0,
        anomaly_at: Optional[int] = None,
        anomaly: Optional[AnomalyType] = None,
        anomaly_node: Optional[str] = None,
    ):
        """Yields one snapshot (list of node dicts) per tick. Anomaly (if any)
        starts at tick `anomaly_at` and persists for the rest of the stream."""
        start = time.time()
        for i in range(ticks):
            active_anomaly = anomaly if (anomaly_at is not None and i >= anomaly_at) else None
            yield self.generate_snapshot(
                anomaly=active_anomaly,
                anomaly_node=anomaly_node,
                ts=start + i * interval_s,
            )