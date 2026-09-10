from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ApprovalStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED  = "EXPIRED"


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    strategy: str
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    notes: Optional[str] = None


class HumanInTheLoop:
    """
    Feature #45 - Human-in-the-Loop.
    Queues recovery actions for human approval before execution.
    The Decision Engine calls this when confidence is low or
    the risk level is high.
    """

    def __init__(self, auto_approve_above: float = 0.90) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self.auto_approve_above = auto_approve_above

    def request_approval(
        self,
        node_id: str,
        strategy: str,
        reason: str,
        confidence: float = 0.0,
    ) -> ApprovalRequest:
        req = ApprovalRequest(node_id=node_id, strategy=strategy, reason=reason)
        # Auto-approve if confidence is high enough
        if confidence >= self.auto_approve_above:
            req.status = ApprovalStatus.APPROVED
            req.decided_by = "auto"
            req.decided_at = datetime.now(timezone.utc)
            req.notes = f"Auto-approved: confidence {confidence:.0%} >= threshold {self.auto_approve_above:.0%}"
        self._requests[req.request_id] = req
        return req

    def approve(self, request_id: str, operator: str, notes: str = "") -> ApprovalRequest:
        req = self._get(request_id)
        req.status = ApprovalStatus.APPROVED
        req.decided_by = operator
        req.decided_at = datetime.now(timezone.utc)
        req.notes = notes
        return req

    def reject(self, request_id: str, operator: str, notes: str = "") -> ApprovalRequest:
        req = self._get(request_id)
        req.status = ApprovalStatus.REJECTED
        req.decided_by = operator
        req.decided_at = datetime.now(timezone.utc)
        req.notes = notes
        return req

    def pending(self) -> List[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]

    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def _get(self, request_id: str) -> ApprovalRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Request {request_id} not found")
        return req
