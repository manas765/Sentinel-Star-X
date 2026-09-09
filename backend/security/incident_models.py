from dataclasses import dataclass


@dataclass
class IncidentSignals:
    """Raw signals gathered from other modules for one incident."""
    entity_id: str
    security_risk: float = 0.0       # 0.0-1.0, from SecurityAnomalyDetector (#13)
    failure_risk: float = 0.0        # 0.0-1.0, from predictive failure detection (#7, future)
    packet_loss_percent: float = 0.0
    latency_ms: float = 0.0
    traffic_ratio: float = 1.0       # current traffic / baseline traffic
    recent_config_change: bool = False


@dataclass
class IncidentClassification:
    """Probability breakdown across the four possible causes."""
    entity_id: str
    hardware_failure: float
    congestion: float
    configuration_error: float
    security_incident: float

    @property
    def probable_cause(self) -> str:
        scores = {
            "hardware_failure": self.hardware_failure,
            "congestion": self.congestion,
            "configuration_error": self.configuration_error,
            "security_incident": self.security_incident,
        }
        return max(scores, key=scores.get)