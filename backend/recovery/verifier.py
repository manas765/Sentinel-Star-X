from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class VerificationResult(BaseModel):
    node_id: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checks_passed: List[str] = []
    checks_failed: List[str] = []
    success: bool = False
    confidence: float = 0.0  # 0.0 - 1.0


class RecoveryVerifier:
    """
    Feature #28 - Recovery Verification.
    Checks whether a recovery actually worked by running
    a series of health checks on the recovered node.
    """

    def verify(self, node_id: str, node_state: Dict) -> VerificationResult:
        passed = []
        failed = []

        if node_state.get("reachable", False):
            passed.append("node_reachable")
        else:
            failed.append("node_reachable")

        if node_state.get("services_up", False):
            passed.append("services_up")
        else:
            failed.append("services_up")

        if node_state.get("latency_ms", 9999) < 200:
            passed.append("latency_acceptable")
        else:
            failed.append("latency_acceptable")

        if node_state.get("error_rate", 1.0) < 0.05:
            passed.append("error_rate_normal")
        else:
            failed.append("error_rate_normal")

        total = len(passed) + len(failed)
        confidence = len(passed) / total if total > 0 else 0.0
        success = len(failed) == 0

        return VerificationResult(
            node_id=node_id,
            checks_passed=passed,
            checks_failed=failed,
            success=success,
            confidence=round(confidence, 2),
        )
