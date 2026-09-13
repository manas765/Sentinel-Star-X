"""
backend/digital_twin/drift.py

Digital Twin Drift Detection (feature 6.57).

Compares two mirrored states (from DigitalTwin.get_state()) and reports
how much they've diverged. This is a general compare-any-two-states tool,
not hardwired to a specific pair - because right now, the "real network"
and the "digital twin" ARE the same simulator, so a real-vs-twin
comparison would always read zero and that number would be meaningless.

What it's genuinely useful for TODAY: comparing the real twin against a
forked sandbox twin (backend/digital_twin/sandbox.py) after a what-if
scenario, or across two ticks of the same twin, to see how much random
telemetry noise alone moves the numbers. Once a truly independent "real"
data source exists, point this at (real_state, twin_state) instead - the
comparison logic doesn't change.
"""

from __future__ import annotations

from dataclasses import dataclass

_NUMERIC_FIELDS = ["latency_ms", "packet_loss_pct", "throughput_mbps", "cpu_util_pct"]


@dataclass
class DriftReport:
    drift_score: float                 # 0.0 (identical) - 1.0 (fully diverged)
    affected_components: list
    topology_diff: bool
    sync_status: str                   # "in_sync" | "minor_drift" | "significant_drift"
    recommended_action: str


class DriftDetector:
    def __init__(self, minor_threshold: float = 0.1, significant_threshold: float = 0.35):
        self.minor_threshold = minor_threshold
        self.significant_threshold = significant_threshold

    def compare(self, state_a: dict, state_b: dict) -> DriftReport:
        nodes_a = {n["node_id"]: n for n in state_a["nodes"]}
        nodes_b = {n["node_id"]: n for n in state_b["nodes"]}

        affected = []
        per_node_drift = []

        all_ids = set(nodes_a) | set(nodes_b)
        for node_id in all_ids:
            a, b = nodes_a.get(node_id), nodes_b.get(node_id)
            if a is None or b is None:
                affected.append(node_id)
                per_node_drift.append(1.0)
                continue

            if a["status"] != b["status"]:
                affected.append(node_id)
                per_node_drift.append(1.0)
                continue

            field_diffs = []
            for field in _NUMERIC_FIELDS:
                va, vb = a.get(field, 0.0), b.get(field, 0.0)
                scale = max(abs(va), abs(vb), 1.0)  # avoid div-by-zero, normalize
                field_diffs.append(abs(va - vb) / scale)
            node_drift = sum(field_diffs) / len(field_diffs)
            per_node_drift.append(node_drift)
            if node_drift > self.minor_threshold:
                affected.append(node_id)

        drift_score = round(sum(per_node_drift) / len(per_node_drift), 4) if per_node_drift else 0.0
        topology_diff = state_a.get("topology_version") != state_b.get("topology_version")

        if topology_diff or drift_score >= self.significant_threshold:
            sync_status = "significant_drift"
            action = "Full resync recommended - topology or multiple metrics have diverged materially."
        elif drift_score >= self.minor_threshold:
            sync_status = "minor_drift"
            action = "Resync affected nodes on next tick; likely just telemetry noise or a small pending change."
        else:
            sync_status = "in_sync"
            action = "No action needed."

        return DriftReport(
            drift_score=drift_score,
            affected_components=sorted(set(affected)),
            topology_diff=topology_diff,
            sync_status=sync_status,
            recommended_action=action,
        )
