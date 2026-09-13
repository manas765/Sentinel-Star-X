"""
backend/digital_twin/twin.py

Digital Twin (feature 6.4).

Mirrors the live network's topology + telemetry (nodes, links, traffic,
latency, packet loss, bandwidth, failures) by reading from a
NetworkSimulator + TelemetryGenerator pair. Health/trust/security-state
overlays are attached separately via attach_* methods, since those are
owned by other engines (Network Health Engine, Trust Engine, Security
modules) that don't exist as part of this module - the twin just gives
them somewhere to write their scores against a node_id.

fork() is the key method for the Sandbox / What-If Lab (6.5): it produces
an independent copy of the current network state that can be mutated
freely (fail a node, cut a link, etc.) without ever touching the real
simulator this twin mirrors.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field

from backend.network.simulator import NetworkSimulator
from backend.telemetry.generator import TelemetryGenerator
from backend.telemetry.schema import TelemetrySnapshot


@dataclass
class NodeOverlay:
    """Scores computed by OTHER engines, attached here so the twin's view
    of a node is complete. All optional/None until those engines exist."""
    health_score: float | None = None
    trust_score: float | None = None
    security_state: str | None = None


class DigitalTwin:
    def __init__(self, source: NetworkSimulator, seed: int | None = None):
        self.source = source
        self._generator = TelemetryGenerator(source, seed=seed)
        self.latest_snapshot: TelemetrySnapshot | None = None
        self.last_synced_at: float | None = None
        self._overlays: dict[str, NodeOverlay] = {
            node_id: NodeOverlay() for node_id in source.devices
        }

    def sync(self) -> TelemetrySnapshot:
        """Pull the newest topology + telemetry from the source network.
        Call this once per tick to keep the twin from drifting (see
        feature 6.57, Digital Twin Drift Detection, for measuring how
        well this stays in sync)."""
        for node_id in self.source.devices:
            self._overlays.setdefault(node_id, NodeOverlay())

        self.latest_snapshot = self._generator.generate_snapshot()
        self.last_synced_at = time.time()
        return self.latest_snapshot

    def attach_health_score(self, node_id: str, score: float):
        self._overlays[node_id].health_score = score

    def attach_trust_score(self, node_id: str, score: float):
        self._overlays[node_id].trust_score = score

    def attach_security_state(self, node_id: str, state: str):
        self._overlays[node_id].security_state = state

    def get_state(self) -> dict:
        """Full mirrored state: topology + latest telemetry + overlays,
        merged per node. This is what the what-if lab and other consumers
        (Copilot, dashboards) should read from - never read the raw
        simulator directly."""
        if self.latest_snapshot is None:
            self.sync()

        topology = self.source.get_topology().to_dict()
        snapshot = self.latest_snapshot.to_dict()

        nodes_by_id = {n["node_id"]: n for n in snapshot["nodes"]}
        for device in topology["devices"]:
            node_id = device["node_id"]
            overlay = self._overlays.get(node_id, NodeOverlay())
            merged = nodes_by_id.get(node_id, {})
            merged.update({
                "device_type": device["device_type"],
                "ip_address": device["ip_address"],
                "priority": device["priority"],
                "is_central": device["is_central"],
                "health_score": overlay.health_score,
                "trust_score": overlay.trust_score,
                "security_state": overlay.security_state,
            })

        return {
            "topology_version": topology["version"],
            "last_synced_at": self.last_synced_at,
            "tick": snapshot["tick"],
            "nodes": list(nodes_by_id.values()),
            "links": snapshot["links"],
        }

    def fork(self, seed: int | None = None) -> "DigitalTwin":
        """Produce an independent Digital Twin over a DEEP COPY of the
        current network state. Mutating the fork (fail_node, cut a link,
        change bandwidth, etc.) never affects the real network or this
        twin - this is what the Sandbox / What-If Lab (6.5) builds on."""
        forked_source = copy.deepcopy(self.source)
        forked_twin = DigitalTwin(forked_source, seed=seed)
        forked_twin._overlays = copy.deepcopy(self._overlays)
        forked_twin.sync()
        return forked_twin
