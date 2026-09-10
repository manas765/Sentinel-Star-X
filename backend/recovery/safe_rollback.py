from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class RollbackSnapshot(BaseModel):
    """State saved before a recovery attempt so we can undo it."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    saved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: Dict


class RollbackResult(BaseModel):
    node_id: str
    snapshot_id: str
    success: bool
    rolled_back_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str


class SafeRollback:
    """
    Feature #48 - Safe Rollback.
    Saves network state before recovery and restores it if
    verification fails or the operator requests a rollback.
    """

    def __init__(self) -> None:
        self._snapshots: Dict[str, RollbackSnapshot] = {}

    def save(self, node_id: str, state: Dict) -> RollbackSnapshot:
        snap = RollbackSnapshot(node_id=node_id, state=state)
        self._snapshots[node_id] = snap
        return snap

    def rollback(self, node_id: str, reason: str = "manual") -> RollbackResult:
        snap = self._snapshots.get(node_id)
        if snap is None:
            return RollbackResult(
                node_id=node_id,
                snapshot_id="none",
                success=False,
                reason=f"No snapshot found for {node_id}",
            )
        # In a real system this would apply the state back to the network
        return RollbackResult(
            node_id=node_id,
            snapshot_id=snap.snapshot_id,
            success=True,
            reason=reason,
        )

    def has_snapshot(self, node_id: str) -> bool:
        return node_id in self._snapshots

    def get_snapshot(self, node_id: str) -> Optional[RollbackSnapshot]:
        return self._snapshots.get(node_id)

    def clear(self, node_id: str) -> None:
        self._snapshots.pop(node_id, None)
