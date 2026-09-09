from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class SLATarget:
    """The committed service-level targets for one entity."""
    entity_id: str
    name: str
    uptime_target_percent: float = 99.9
    max_response_time_ms: float = 200.0
    max_allowed_packet_loss_percent: float = 1.0


@dataclass
class SLAViolation:
    timestamp: str
    metric: str
    target: float
    actual: float
    severity: str  # "MINOR", "MAJOR", "CRITICAL"


@dataclass
class SLAStatus:
    entity_id: str
    name: str
    is_compliant: bool
    uptime_percent: float
    current_response_time_ms: float
    current_packet_loss_percent: float
    violations: List[SLAViolation] = field(default_factory=list)