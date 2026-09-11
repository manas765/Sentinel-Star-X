from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class SurvivalModeEvent:
    timestamp: str
    action: str  # "ACTIVATED" or "DEACTIVATED"
    reason: str


@dataclass
class SurvivalModeState:
    is_active: bool = False
    activated_at: str = ""
    history: List[SurvivalModeEvent] = field(default_factory=list)


@dataclass
class SurvivalModeAssessment:
    should_activate: bool
    critical_services_at_risk: int
    total_critical_services: int
    entities_in_high_threat: int
    total_entities: int
    reason: str