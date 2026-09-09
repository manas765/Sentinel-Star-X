from dataclasses import dataclass, field
from typing import List


@dataclass
class CriticalService:
    """A network entity marked as business/mission critical."""
    entity_id: str
    name: str
    priority: int = 1  # 1 = highest priority, higher numbers = lower priority
    dependent_services: List[str] = field(default_factory=list)


@dataclass
class ProtectionStatus:
    """Current protection assessment for one critical service."""
    entity_id: str
    is_critical: bool
    priority: int
    effective_threat_level: str
    requires_immediate_action: bool
    reason: str