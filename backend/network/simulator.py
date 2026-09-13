"""
backend/network/simulator.py

Intelligent Network Simulator (feature 6.1).

Owns the live, mutable state of a Star topology: devices, links, and the
"knobs" (traffic multipliers, forced latency/packet-loss, failure state) that
let other modules or a UI drive scenarios. This is the single source of
truth that backend/telemetry/generator.py reads from to produce
TelemetrySnapshot objects every tick.

Does NOT compute health scores or trust — those are separate engines
(Network Health Engine 6.3, Trust Engine) that read from this simulator's
output, they don't live inside it.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from backend.network.models import Device, DeviceType, Link, Topology


def _random_mac(rng: random.Random) -> str:
    return ":".join(f"{rng.randint(0, 255):02x}" for _ in range(6))


@dataclass
class _NodeState:
    """Internal mutable state per node - not part of the public contract."""
    disabled: bool = False
    failed: bool = False
    traffic_multiplier: float = 1.0
    forced_latency_ms: float | None = None
    forced_packet_loss_pct: float | None = None


@dataclass
class _LinkState:
    disabled: bool = False
    failed: bool = False
    capacity_mbps: float = 100.0


class NetworkSimulator:
    def __init__(self, num_leaves: int = 8, seed: int | None = None):
        self._rng = random.Random(seed)
        self._version = 1
        self.devices: dict[str, Device] = {}
        self.links: dict[str, Link] = {}
        self._node_state: dict[str, _NodeState] = {}
        self._link_state: dict[str, _LinkState] = {}

        self.central_id = "central"
        self._add_device(self.central_id, DeviceType.CENTRAL_SWITCH, priority=5, is_central=True)

        for i in range(num_leaves):
            node_id = f"leaf-{i}"
            dtype = self._rng.choice(
                [DeviceType.PC, DeviceType.PC, DeviceType.SERVER_DB,
                 DeviceType.SERVER_AUTH, DeviceType.IOT, DeviceType.GUEST]
            )
            priority = 5 if dtype in (DeviceType.SERVER_DB, DeviceType.SERVER_AUTH) else 2
            self._add_device(node_id, dtype, priority=priority)
            self._add_link(node_id, self.central_id, capacity_mbps=100.0)

    # ---------- internal helpers ----------

    def _add_device(self, node_id: str, dtype: DeviceType, priority: int, is_central: bool = False):
        self.devices[node_id] = Device(
            node_id=node_id,
            device_type=dtype,
            ip_address=f"10.0.0.{len(self.devices) + 1}",
            mac_address=_random_mac(self._rng),
            priority=priority,
            is_central=is_central,
        )
        self._node_state[node_id] = _NodeState()
        self._version += 1

    def _add_link(self, source_id: str, target_id: str, capacity_mbps: float):
        link_id = f"{source_id}<->{target_id}"
        self.links[link_id] = Link(link_id, source_id, target_id, capacity_mbps)
        self._link_state[link_id] = _LinkState(capacity_mbps=capacity_mbps)
        self._version += 1

    def _link_for_node(self, node_id: str) -> str | None:
        for link_id, link in self.links.items():
            if link.source_id == node_id or link.target_id == node_id:
                return link_id
        return None

    # ---------- 6.1 capabilities ----------

    def add_node(self, dtype: DeviceType, priority: int = 2) -> str:
        node_id = f"leaf-{len(self.devices)}"
        self._add_device(node_id, dtype, priority)
        self._add_link(node_id, self.central_id, capacity_mbps=100.0)
        return node_id

    def remove_node(self, node_id: str):
        if node_id == self.central_id:
            raise ValueError("cannot remove the central switch")
        link_id = self._link_for_node(node_id)
        if link_id:
            del self.links[link_id]
            del self._link_state[link_id]
        del self.devices[node_id]
        del self._node_state[node_id]
        self._version += 1

    def disable_node(self, node_id: str):
        self._node_state[node_id].disabled = True

    def restore_node(self, node_id: str):
        state = self._node_state[node_id]
        state.disabled = False
        state.failed = False
        state.forced_latency_ms = None
        state.forced_packet_loss_pct = None
        state.traffic_multiplier = 1.0

    def create_link(self, source_id: str, target_id: str, capacity_mbps: float = 100.0) -> str:
        self._add_link(source_id, target_id, capacity_mbps)
        return f"{source_id}<->{target_id}"

    def remove_link(self, link_id: str):
        del self.links[link_id]
        del self._link_state[link_id]
        self._version += 1

    def set_bandwidth(self, link_id: str, capacity_mbps: float):
        self._link_state[link_id].capacity_mbps = capacity_mbps
        self.links[link_id].capacity_mbps = capacity_mbps

    def set_traffic_multiplier(self, node_id: str, multiplier: float):
        self._node_state[node_id].traffic_multiplier = max(0.0, multiplier)

    def simulate_latency(self, node_id: str, latency_ms: float | None):
        self._node_state[node_id].forced_latency_ms = latency_ms

    def simulate_packet_loss(self, node_id: str, packet_loss_pct: float | None):
        self._node_state[node_id].forced_packet_loss_pct = packet_loss_pct

    def fail_node(self, node_id: str):
        self._node_state[node_id].failed = True

    def fail_link(self, link_id: str):
        self._link_state[link_id].failed = True

    def degrade_switch(self, switch_id: str, latency_ms: float, packet_loss_pct: float):
        """Degrade (not fail) a switch - e.g. central switch under load."""
        self.simulate_latency(switch_id, latency_ms)
        self.simulate_packet_loss(switch_id, packet_loss_pct)

    # ---------- output ----------

    def get_topology(self) -> Topology:
        return Topology(
            version=self._version,
            devices=list(self.devices.values()),
            links=list(self.links.values()),
        )

    def node_state(self, node_id: str) -> _NodeState:
        return self._node_state[node_id]

    def link_state(self, link_id: str) -> _LinkState:
        return self._link_state[link_id]
