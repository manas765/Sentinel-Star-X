from dataclasses import dataclass, field
from typing import List


@dataclass
class SecurityEvent:
    """A single flagged event for one entity, with enough context to correlate against others."""
    entity_id: str
    timestamp: str
    risk_score: float
    flags: List[str] = field(default_factory=list)
    related_peers: List[str] = field(default_factory=list)  # entities this one communicated with


@dataclass
class FusedIncident:
    """One or more correlated events merged into a single incident."""
    incident_id: str
    entity_ids: List[str]
    combined_risk_score: float
    correlation_reason: str
    event_count: int