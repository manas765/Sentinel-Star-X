"""
backend/network/time_machine.py

Network Time Machine (feature 6.39).

Allows historical inspection of topology, health, and traffic by keeping a
rolling buffer of past DigitalTwin.get_state() snapshots. Bounded by
max_snapshots so this doesn't grow memory unboundedly in a long-running
process - old snapshots roll off. Trust and incident history are NOT
stored here (those belong to the Trust and Recovery/Network-Memory
tracks); get_snapshot_at() returns whatever the twin's state had at that
point, and other tracks' historical data should be joined in by timestamp
on their end rather than duplicated into this store.
"""

from __future__ import annotations

import bisect
import time
from dataclasses import dataclass


@dataclass
class TimestampedSnapshot:
    timestamp: float
    tick: int
    state: dict


class NetworkTimeMachine:
    def __init__(self, max_snapshots: int = 2000):
        self.max_snapshots = max_snapshots
        self._snapshots: list = []
        self._timestamps: list = []  # kept parallel + sorted for bisect lookup

    def record(self, state: dict):
        entry = TimestampedSnapshot(
            timestamp=state.get("last_synced_at") or time.time(),
            tick=state["tick"],
            state=state,
        )
        self._snapshots.append(entry)
        self._timestamps.append(entry.timestamp)

        if len(self._snapshots) > self.max_snapshots:
            self._snapshots.pop(0)
            self._timestamps.pop(0)

    def get_snapshot_at(self, timestamp: float) -> TimestampedSnapshot | None:
        """Nearest snapshot at or before the given timestamp - i.e. 'what
        did the network look like at this point in time'."""
        if not self._timestamps:
            return None
        idx = bisect.bisect_right(self._timestamps, timestamp) - 1
        if idx < 0:
            return None
        return self._snapshots[idx]

    def get_range(self, start_ts: float, end_ts: float) -> list:
        return [s for s in self._snapshots if start_ts <= s.timestamp <= end_ts]

    def get_latest(self) -> TimestampedSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def node_history(self, node_id: str, limit: int = 100) -> list:
        """Convenience: just one node's status/health over time, for
        post-incident analysis without re-parsing full snapshots."""
        results = []
        for snap in self._snapshots[-limit:]:
            node = next((n for n in snap.state["nodes"] if n["node_id"] == node_id), None)
            if node:
                results.append({
                    "timestamp": snap.timestamp,
                    "tick": snap.tick,
                    "status": node["status"],
                    "health_score": node.get("health_score"),
                    "latency_ms": node["latency_ms"],
                    "packet_loss_pct": node["packet_loss_pct"],
                })
        return results

    def __len__(self):
        return len(self._snapshots)
