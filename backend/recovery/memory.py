from __future__ import annotations
from typing import Dict, List, Optional
from .models import NetworkSnapshot, RecoveryEvent


class NetworkMemory:
    """
    Feature #30 — Network Memory.

    Stores the history of network snapshots and recovery events so the
    system can learn from past behaviour. Everything else (Knowledge Base,
    Strategy Simulator, Decision Engine) reads from here.
    """

    def __init__(self, max_snapshots: int = 500) -> None:
        self._snapshots: Dict[str, NetworkSnapshot] = {}
        self._events: List[RecoveryEvent] = []
        self._max_snapshots = max_snapshots

    # ── Snapshots ────────────────────────────────────────────────────────────

    def save_snapshot(self, snapshot: NetworkSnapshot) -> NetworkSnapshot:
        """Store a network state snapshot. Evicts oldest if over limit."""
        if len(self._snapshots) >= self._max_snapshots:
            oldest_key = next(iter(self._snapshots))
            del self._snapshots[oldest_key]
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[NetworkSnapshot]:
        return self._snapshots.get(snapshot_id)

    def latest_snapshot(self) -> Optional[NetworkSnapshot]:
        if not self._snapshots:
            return None
        return list(self._snapshots.values())[-1]

    def all_snapshots(self) -> List[NetworkSnapshot]:
        return list(self._snapshots.values())

    def snapshots_with_failures(self) -> List[NetworkSnapshot]:
        """Return only snapshots where nodes were failing — useful for pattern analysis."""
        return [s for s in self._snapshots.values() if s.failed_nodes]

    # ── Recovery Events ───────────────────────────────────────────────────────

    def record_event(self, event: RecoveryEvent) -> RecoveryEvent:
        self._events.append(event)
        return event

    def get_events(self) -> List[RecoveryEvent]:
        return list(self._events)

    def successful_events(self) -> List[RecoveryEvent]:
        return [e for e in self._events if e.success]

    def failed_events(self) -> List[RecoveryEvent]:
        return [e for e in self._events if not e.success]

    def events_for_node(self, node_id: str) -> List[RecoveryEvent]:
        return [e for e in self._events if node_id in e.affected_nodes]

    def events_for_strategy(self, strategy: str) -> List[RecoveryEvent]:
        return [e for e in self._events if e.strategy_used == strategy]

    # ── Stats (used by Decision Engine later) ────────────────────────────────

    def strategy_success_rate(self, strategy: str) -> float:
        """Returns 0.0–1.0 success rate for a given strategy. 0.0 if never used."""
        relevant = self.events_for_strategy(strategy)
        if not relevant:
            return 0.0
        return sum(1 for e in relevant if e.success) / len(relevant)

    def summary(self) -> dict:
        return {
            "total_snapshots": len(self._snapshots),
            "total_events": len(self._events),
            "successful_recoveries": len(self.successful_events()),
            "failed_recoveries": len(self.failed_events()),
        }