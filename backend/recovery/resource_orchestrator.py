from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ResourceSnapshot(BaseModel):
    """Current resource availability on the network."""
    cpu_available: float        # 0.0 - 1.0
    memory_available: float     # 0.0 - 1.0
    bandwidth_available: float  # 0.0 - 1.0
    active_recovery_jobs: int = 0


class ResourceRequirement(BaseModel):
    """Resources needed to execute a recovery strategy."""
    strategy: str
    cpu_needed: float
    memory_needed: float
    bandwidth_needed: float


class OrchestrationDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    strategy: str
    approved: bool
    reason: str
    queued: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResourceAwareOrchestrator:
    """
    Feature #63 - Resource-Aware Recovery Orchestration.
    Checks whether the network has enough CPU, memory, and bandwidth
    to run a recovery strategy before approving it. Queues recoveries
    that cannot run immediately due to resource constraints.
    """

    # Resource requirements per strategy
    REQUIREMENTS: Dict[str, ResourceRequirement] = {
        "reroute":  ResourceRequirement(strategy="reroute",  cpu_needed=0.10, memory_needed=0.05, bandwidth_needed=0.20),
        "restart":  ResourceRequirement(strategy="restart",  cpu_needed=0.30, memory_needed=0.20, bandwidth_needed=0.10),
        "failover": ResourceRequirement(strategy="failover", cpu_needed=0.25, memory_needed=0.30, bandwidth_needed=0.25),
        "isolate":  ResourceRequirement(strategy="isolate",  cpu_needed=0.05, memory_needed=0.05, bandwidth_needed=0.05),
    }

    def __init__(self) -> None:
        self._queue: List[OrchestrationDecision] = []
        self._history: List[OrchestrationDecision] = []

    def can_run(self, strategy: str, resources: ResourceSnapshot) -> tuple[bool, str]:
        req = self.REQUIREMENTS.get(strategy)
        if req is None:
            return False, f"Unknown strategy: {strategy}"

        if resources.active_recovery_jobs >= 3:
            return False, "Too many active recovery jobs — queuing."
        if resources.cpu_available < req.cpu_needed:
            return False, f"Insufficient CPU: need {req.cpu_needed:.0%}, have {resources.cpu_available:.0%}."
        if resources.memory_available < req.memory_needed:
            return False, f"Insufficient memory: need {req.memory_needed:.0%}, have {resources.memory_available:.0%}."
        if resources.bandwidth_available < req.bandwidth_needed:
            return False, f"Insufficient bandwidth: need {req.bandwidth_needed:.0%}, have {resources.bandwidth_available:.0%}."

        return True, "Resources sufficient — recovery approved."

    def orchestrate(
        self, node_id: str, strategy: str, resources: ResourceSnapshot
    ) -> OrchestrationDecision:
        approved, reason = self.can_run(strategy, resources)
        decision = OrchestrationDecision(
            node_id=node_id,
            strategy=strategy,
            approved=approved,
            reason=reason,
            queued=not approved,
        )
        if not approved:
            self._queue.append(decision)
        self._history.append(decision)
        return decision

    def queue(self) -> List[OrchestrationDecision]:
        return list(self._queue)

    def history(self) -> List[OrchestrationDecision]:
        return list(self._history)

    def flush_queue(self, resources: ResourceSnapshot) -> List[OrchestrationDecision]:
        """Re-evaluate queued jobs when resources free up."""
        approved = []
        still_queued = []
        for decision in self._queue:
            ok, reason = self.can_run(decision.strategy, resources)
            if ok:
                decision.approved = True
                decision.queued = False
                decision.reason = reason
                approved.append(decision)
            else:
                still_queued.append(decision)
        self._queue = still_queued
        return approved
