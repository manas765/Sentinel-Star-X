"""
backend/telemetry/schema.py

This is the CONTRACT. Anomaly detection, failure prediction, RCA, and the
Digital Twin all consume this shape. Do not change field names/units without
a version bump and a heads-up in #sentinel-dev — everything downstream is
built against this.

Emitted once per tick as a TelemetrySnapshot. Static device metadata
(IP/MAC/device_type/priority) is NOT included here — see
backend/network/models.py for the topology registry, keyed by node_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LinkStatus(str, Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


class NodeStatus(str, Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class NodeTelemetry:
    node_id: str

    status: NodeStatus

    # Resource utilization (0-100)
    cpu_util_pct: float
    mem_util_pct: float

    # Network-layer metrics
    latency_ms: float          # round-trip time to central switch
    jitter_ms: float
    packet_loss_pct: float     # 0-100
    error_rate_pct: float      # 0-100, malformed/dropped-at-NIC packets

    # Throughput (actual, measured) vs the link's provisioned capacity
    # (capacity lives on the Link object in network/models.py, not here)
    throughput_mbps: float
    traffic_in_mbps: float
    traffic_out_mbps: float

    connection_count: int
    uptime_s: float

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["status"] = self.status.value
        return d


@dataclass
class LinkTelemetry:
    link_id: str            # matches Link.link_id from network/models.py
    status: LinkStatus
    utilization_pct: float  # current throughput / capacity_mbps, 0-100+
    latency_ms: float
    packet_loss_pct: float

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["status"] = self.status.value
        return d


@dataclass
class TelemetrySnapshot:
    tick: int                  # monotonically increasing, resets on sim restart
    timestamp: float           # unix epoch seconds (UTC)
    topology_version: int      # cross-reference to network/models.py Topology.version
    nodes: list = field(default_factory=list)   # list[NodeTelemetry]
    links: list = field(default_factory=list)   # list[LinkTelemetry]

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "topology_version": self.topology_version,
            "nodes": [n.to_dict() for n in self.nodes],
            "links": [l.to_dict() for l in self.links],
        }


# Update interval: fixed at 1.0s for the simulator (matches your generator's
# default). If your model needs a different cadence for training, downsample
# on your side rather than asking the simulator to change tick rate — other
# consumers (Health Engine, Digital Twin sync) are built against 1s.
TICK_INTERVAL_S = 1.0
