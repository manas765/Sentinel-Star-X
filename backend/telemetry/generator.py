"""
backend/telemetry/generator.py

Real-Time Network Monitoring (feature 6.2).

Reads live state from a NetworkSimulator and produces TelemetrySnapshot
objects matching the locked contract in backend/telemetry/schema.py. This
is the ONLY thing downstream modules (AI, Digital Twin, Health Engine)
should read from - never read NetworkSimulator's internal state directly.
"""

from __future__ import annotations

import random
import time

from backend.network.models import DeviceType
from backend.network.simulator import NetworkSimulator
from backend.telemetry.schema import (
    LinkStatus,
    LinkTelemetry,
    NodeStatus,
    NodeTelemetry,
    TelemetrySnapshot,
    TICK_INTERVAL_S,
)


class TelemetryGenerator:
    def __init__(self, simulator: NetworkSimulator, seed: int | None = None):
        self.sim = simulator
        self._rng = random.Random(seed)
        self._tick = 0
        self._uptime: dict[str, float] = {d: 0.0 for d in simulator.devices}

    def _node_telemetry(self, node_id: str) -> NodeTelemetry:
        device = self.sim.devices[node_id]
        state = self.sim.node_state(node_id)
        is_central = device.is_central

        if state.failed:
            status = NodeStatus.DOWN
            self._uptime[node_id] = 0.0
            return NodeTelemetry(
                node_id=node_id, status=status,
                cpu_util_pct=0.0, mem_util_pct=0.0,
                latency_ms=0.0, jitter_ms=0.0,
                packet_loss_pct=100.0, error_rate_pct=100.0,
                throughput_mbps=0.0, traffic_in_mbps=0.0, traffic_out_mbps=0.0,
                connection_count=0, uptime_s=0.0,
            )

        if state.disabled:
            status = NodeStatus.DOWN
        elif state.forced_latency_ms or state.forced_packet_loss_pct:
            status = NodeStatus.DEGRADED
        else:
            status = NodeStatus.UP

        self._uptime[node_id] += TICK_INTERVAL_S

        base_latency = 2.0 if is_central else self._rng.uniform(5.0, 15.0)
        latency = state.forced_latency_ms if state.forced_latency_ms is not None else base_latency

        base_loss = self._rng.uniform(0.0, 0.3)
        packet_loss = (
            state.forced_packet_loss_pct if state.forced_packet_loss_pct is not None else base_loss
        )

        base_traffic = self._rng.uniform(50, 300) if is_central else self._rng.uniform(5, 40)
        traffic = base_traffic * state.traffic_multiplier

        return NodeTelemetry(
            node_id=node_id,
            status=status,
            cpu_util_pct=round(min(100.0, self._rng.uniform(10, 40) * state.traffic_multiplier), 2),
            mem_util_pct=round(self._rng.uniform(20, 60), 2),
            latency_ms=round(latency, 2),
            jitter_ms=round(self._rng.uniform(0.1, 2.0), 2),
            packet_loss_pct=round(min(100.0, packet_loss), 2),
            error_rate_pct=round(self._rng.uniform(0.0, 0.2), 3),
            throughput_mbps=round(traffic, 2),
            traffic_in_mbps=round(traffic * self._rng.uniform(0.4, 0.6), 2),
            traffic_out_mbps=round(traffic * self._rng.uniform(0.4, 0.6), 2),
            connection_count=self._rng.randint(1, 50) if device.device_type != DeviceType.CENTRAL_SWITCH
            else self._rng.randint(50, 500),
            uptime_s=round(self._uptime[node_id], 1),
        )

    def _link_telemetry(self, link_id: str) -> LinkTelemetry:
        link = self.sim.links[link_id]
        state = self.sim.link_state(link_id)

        if state.failed:
            return LinkTelemetry(link_id, LinkStatus.DOWN, 0.0, 0.0, 100.0)
        if state.disabled:
            return LinkTelemetry(link_id, LinkStatus.DOWN, 0.0, 0.0, 100.0)

        node_a_state = self.sim.node_state(link.source_id)
        node_b_state = self.sim.node_state(link.target_id)
        degraded = bool(
            node_a_state.forced_latency_ms or node_b_state.forced_latency_ms
            or node_a_state.forced_packet_loss_pct or node_b_state.forced_packet_loss_pct
        )

        utilization = min(100.0, self._rng.uniform(5, 40) * max(
            node_a_state.traffic_multiplier, node_b_state.traffic_multiplier
        ))

        return LinkTelemetry(
            link_id=link_id,
            status=LinkStatus.DEGRADED if degraded else LinkStatus.UP,
            utilization_pct=round(utilization, 2),
            latency_ms=round(self._rng.uniform(0.5, 5.0), 2),
            packet_loss_pct=round(self._rng.uniform(0.0, 0.5), 2),
        )

    def generate_snapshot(self) -> TelemetrySnapshot:
        self._tick += 1
        topology = self.sim.get_topology()
        return TelemetrySnapshot(
            tick=self._tick,
            timestamp=time.time(),
            topology_version=topology.version,
            nodes=[self._node_telemetry(nid) for nid in self.sim.devices],
            links=[self._link_telemetry(lid) for lid in self.sim.links],
        )

    def stream(self, ticks: int = 50, interval_s: float = TICK_INTERVAL_S):
        for _ in range(ticks):
            yield self.generate_snapshot()
