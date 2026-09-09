from dataclasses import dataclass
from typing import Optional


@dataclass
class RecoveryGateDecision:
    """Result of checking whether a recovery action is safe to proceed."""
    entity_id: str
    allowed: bool
    requires_manual_approval: bool
    reason: str
    recommended_action: str  # "PROCEED", "HOLD_AND_MONITOR", "MANUAL_APPROVAL_REQUIRED", "BLOCK"