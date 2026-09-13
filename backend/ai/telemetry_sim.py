"""
backend/ai/telemetry_sim.py

Synthetic telemetry generator -- rewritten against the REAL contract from
Akshata (backend/telemetry/schema.py + backend/network/models.py), v2.
No more locally-invented field names: this imports her actual dataclasses,
so drift between "what I test against" and "what the real simulator emits"
is no longer possible by construction.

What changed from v1:
- is_central moved out of telemetry entirely, into the static Device
  registry (topology). Detectors now need a central_node_id passed in
  separately to know which node is which type.
- bandwidth_mbps is gone. throughput_mbps (node-level, actual measured) and
  utilization_pct (link-level, throughput/capacity) replace it -- they mean
  different things now, don't conflate them.
- Links carry their own telemetry (LinkTelemetry), independent of nodes --
  so anomalies can now target a node OR a link. See AnomalyType below.
- New node fields (cpu_util_pct, mem_util_pct, jitter_ms, error_rate_pct,
  connection_count, uptime_s) are populated with baseline ranges.
"""

from __future__ import annotations

import random
import time
from enum import Enum
from typing import Optional

from backend.network.models import Device, DeviceType, Link, Topology
from backend.telemetry.schema import (
    LinkStatus,
    LinkTelemetry,
    NodeStatus,
    NodeTelemetry,
    TelemetrySnapshot,
)


class AnomalyType(str, Enum):
    # Node-level
    NODE_DOWN = "node_down"
    NODE_OVERLOAD = "node_overload"       # high cpu/mem/latency/error_rate
    LATENCY_SPIKE = "latency_spike"       # node latency/jitter spike
    PACKET_LOSS = "packet_loss"           # node packet_loss/error_rate spike
    # Link-level -- new in v2, only possible because links now have their
    # own telemetry independent of the nodes they connect.
    LINK_DOWN = "link_down"
    LINK_CONGESTION = "link_congestion"   # utilization_pct spike


NODE_ANOMALIES = {
    AnomalyType.NODE_DOWN,
    AnomalyType.NODE_OVERLOAD,
    AnomalyType.LATENCY_SPIKE,
    AnomalyType.PACKET_LOSS,
}
LINK_ANOMALIES = {AnomalyType.LINK_DOWN, AnomalyType.LINK_CONGESTION}


class SyntheticTelemetryGenerator:
    """
    Simulates a star topology: one central switch + N leaf nodes, each leaf
    connected to the central switch by its own link.

    Usage:
        gen = SyntheticTelemetryGenerator(num_leaves=8, seed=42)
        snap = gen.generate_snapshot()                                  # TelemetrySnapshot
        snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN,
                                      anomaly_target="leaf-3")           # node_id
        snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_CONGESTION,
                                      anomaly_target="central<->leaf-3") # link_id
        for snap in gen.stream(ticks=100, anomaly_at=50,
                                anomaly=AnomalyType.LATENCY_SPIKE):
            ...

    gen.topology gives the static Device/Link registry.
    gen.central_node_id gives the one central node's id, needed by
    detectors since telemetry itself no longer says is_central.
    """

    def __init__(self, num_leaves: int = 8, seed: Optional[int] = None):
        self.num_leaves = num_leaves
        self.central_id = "central"
        self.leaf_ids = [f"leaf-{i}" for i in range(num_leaves)]
        self._rng = random.Random(seed)
        self._tick = 0
        self.topology_version = 1
        self.topology = self._build_topology()

    @property
    def central_node_id(self) -> str:
        return self.central_id

    def _fake_mac(self) -> str:
        return ":".join(f"{self._rng.randint(0, 255):02x}" for _ in range(6))

    def _build_topology(self) -> Topology:
        devices = [
            Device(
                node_id=self.central_id,
                device_type=DeviceType.CENTRAL_SWITCH,
                ip_address="10.0.0.1",
                mac_address=self._fake_mac(),
                priority=5,
                is_central=True,
            )
        ]
        links = []
        for i, leaf_id in enumerate(self.leaf_ids):
            devices.append(
                Device(
                    node_id=leaf_id,
                    device_type=DeviceType.PC,
                    ip_address=f"10.0.0.{i + 2}",
                    mac_address=self._fake_mac(),
                    priority=self._rng.randint(1, 3),
                    is_central=False,
                )
            )
            links.append(
                Link(
                    link_id=f"{self.central_id}<->{leaf_id}",
                    source_id=self.central_id,
                    target_id=leaf_id,
                    capacity_mbps=100.0,
                )
            )
        return Topology(version=self.topology_version, devices=devices, links=links)

    def _baseline_node(self, node_id: str, is_central: bool) -> NodeTelemetry:
        return NodeTelemetry(
            node_id=node_id,
            status=NodeStatus.UP,
            cpu_util_pct=round(self._rng.uniform(20, 50) if is_central else self._rng.uniform(5, 30), 2),
            mem_util_pct=round(self._rng.uniform(30, 60) if is_central else self._rng.uniform(10, 40), 2),
            latency_ms=round(self._rng.uniform(1.0, 5.0) if is_central else self._rng.uniform(5.0, 20.0), 2),
            jitter_ms=round(self._rng.uniform(0.1, 1.0), 2),
            packet_loss_pct=round(self._rng.uniform(0.0, 0.5), 3),
            error_rate_pct=round(self._rng.uniform(0.0, 0.2), 3),
            throughput_mbps=round(self._rng.uniform(300, 800) if is_central else self._rng.uniform(5, 60), 2),
            traffic_in_mbps=round(self._rng.uniform(50, 400) if is_central else self._rng.uniform(5, 40), 2),
            traffic_out_mbps=round(self._rng.uniform(50, 400) if is_central else self._rng.uniform(5, 40), 2),
            connection_count=self._rng.randint(50, 500) if is_central else self._rng.randint(1, 20),
            uptime_s=round(self._rng.uniform(10000, 500000), 1),
        )

    def _baseline_link(self, link: Link) -> LinkTelemetry:
        return LinkTelemetry(
            link_id=link.link_id,
            status=LinkStatus.UP,
            utilization_pct=round(self._rng.uniform(5, 40), 2),
            latency_ms=round(self._rng.uniform(1.0, 10.0), 2),
            packet_loss_pct=round(self._rng.uniform(0.0, 0.5), 3),
        )

    def generate_snapshot(
        self,
        anomaly: Optional[AnomalyType] = None,
        anomaly_target: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> TelemetrySnapshot:
        ts = ts if ts is not None else time.time()
        nodes = [self._baseline_node(self.central_id, True)]
        nodes += [self._baseline_node(nid, False) for nid in self.leaf_ids]
        links = [self._baseline_link(link) for link in self.topology.links]

        if anomaly in NODE_ANOMALIES:
            target = anomaly_target or self._rng.choice(self.leaf_ids)
            nodes = [self._apply_node_anomaly(n, anomaly) if n.node_id == target else n for n in nodes]
        elif anomaly in LINK_ANOMALIES:
            all_link_ids = [link.link_id for link in self.topology.links]
            target = anomaly_target or self._rng.choice(all_link_ids)
            links = [self._apply_link_anomaly(l, anomaly) if l.link_id == target else l for l in links]

        self._tick += 1
        return TelemetrySnapshot(
            tick=self._tick,
            timestamp=ts,
            topology_version=self.topology_version,
            nodes=nodes,
            links=links,
        )

    def _apply_node_anomaly(self, node: NodeTelemetry, anomaly: AnomalyType) -> NodeTelemetry:
        if anomaly == AnomalyType.NODE_DOWN:
            node.status = NodeStatus.DOWN
            node.cpu_util_pct = 0.0
            node.mem_util_pct = 0.0
            node.latency_ms = 0.0
            node.jitter_ms = 0.0
            node.packet_loss_pct = 100.0
            node.error_rate_pct = 100.0
            node.throughput_mbps = 0.0
            node.traffic_in_mbps = 0.0
            node.traffic_out_mbps = 0.0
            node.connection_count = 0
        elif anomaly == AnomalyType.NODE_OVERLOAD:
            node.status = NodeStatus.DEGRADED
            node.cpu_util_pct = round(self._rng.uniform(85, 100), 2)
            node.mem_util_pct = round(self._rng.uniform(85, 100), 2)
            node.latency_ms *= self._rng.uniform(5, 10)
            node.error_rate_pct = round(self._rng.uniform(5, 20), 2)
        elif anomaly == AnomalyType.LATENCY_SPIKE:
            node.status = NodeStatus.DEGRADED
            node.latency_ms *= self._rng.uniform(8, 20)
            node.jitter_ms *= self._rng.uniform(5, 15)
        elif anomaly == AnomalyType.PACKET_LOSS:
            node.status = NodeStatus.DEGRADED
            node.packet_loss_pct = round(self._rng.uniform(15, 60), 2)
            node.error_rate_pct = round(self._rng.uniform(5, 25), 2)
        return node

    def _apply_link_anomaly(self, link: LinkTelemetry, anomaly: AnomalyType) -> LinkTelemetry:
        if anomaly == AnomalyType.LINK_DOWN:
            link.status = LinkStatus.DOWN
            link.utilization_pct = 0.0
            link.latency_ms = 0.0
            link.packet_loss_pct = 100.0
        elif anomaly == AnomalyType.LINK_CONGESTION:
            link.status = LinkStatus.DEGRADED
            link.utilization_pct = round(self._rng.uniform(90, 150), 2)
            link.latency_ms *= self._rng.uniform(3, 8)
            link.packet_loss_pct = round(self._rng.uniform(2, 15), 2)
        return link

    def stream(
        self,
        ticks: int = 50,
        interval_s: float = 1.0,
        anomaly_at: Optional[int] = None,
        anomaly: Optional[AnomalyType] = None,
        anomaly_target: Optional[str] = None,
    ):
        """Yields one TelemetrySnapshot per tick. Anomaly (if any) starts
        at tick `anomaly_at` and persists for the rest of the stream."""
        start = time.time()
        for i in range(ticks):
            active_anomaly = anomaly if (anomaly_at is not None and i >= anomaly_at) else None
            yield self.generate_snapshot(
                anomaly=active_anomaly,
                anomaly_target=anomaly_target,
                ts=start + i * interval_s,
            )