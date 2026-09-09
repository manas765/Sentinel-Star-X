from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class NetworkSnapshot(BaseModel):
    """A point-in-time capture of the network's state."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    topology: Dict[str, Any] = Field(default_factory=dict)   # nodes + edges
    active_services: List[str] = Field(default_factory=list)
    failed_nodes: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)  # latency, packet loss, etc.
    label: Optional[str] = None                              # e.g. "pre-recovery", "post-recovery"


class RecoveryEvent(BaseModel):
    """Records what happened during a recovery attempt."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger: str                          # what caused the recovery (e.g. "node_failure")
    affected_nodes: List[str]
    strategy_used: str                    # e.g. "reroute", "restart", "failover"
    success: bool
    duration_seconds: float
    pre_snapshot_id: Optional[str] = None
    post_snapshot_id: Optional[str] = None
    notes: Optional[str] = None