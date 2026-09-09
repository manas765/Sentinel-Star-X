from dataclasses import dataclass, field
from typing import List


@dataclass
class NetworkActivitySnapshot:
    """A point-in-time snapshot of one entity's observed network behavior."""
    entity_id: str
    traffic_volume_mbps: float
    baseline_traffic_mbps: float
    connection_count: int
    baseline_connection_count: int
    communicating_with: List[str] = field(default_factory=list)
    authorized_peers: List[str] = field(default_factory=list)
    failed_auth_attempts: int = 0
    is_authorized_device: bool = True


@dataclass
class SecurityAssessment:
    """Result of running anomaly detection against a snapshot."""
    entity_id: str
    risk_score: float  # 0.0 (normal) - 1.0 (severe)
    flags: List[str] = field(default_factory=list)

    @property
    def threat_level(self) -> str:
        if self.risk_score >= 0.75:
            return "CRITICAL"
        if self.risk_score >= 0.5:
            return "HIGH"
        if self.risk_score >= 0.25:
            return "ELEVATED"
        return "NORMAL"