from .incident_models import IncidentSignals, IncidentClassification

# Configurable weights — these turn raw signals into relative scores.
# This is a heuristic baseline; replace with a trained model later if desired.
HARDWARE_FAILURE_RISK_WEIGHT = 3.0
HARDWARE_PACKET_LOSS_WEIGHT = 0.3
CONGESTION_TRAFFIC_WEIGHT = 2.0
CONGESTION_LATENCY_WEIGHT = 0.02
CONFIG_CHANGE_SCORE = 4.0
CONFIG_BASELINE_SCORE = 0.2
SECURITY_RISK_WEIGHT = 4.0

MIN_SCORE_FLOOR = 0.05  # every cause keeps a small nonzero probability


class FailureVsSecurityClassifier:
    """
    Estimates whether an incident is most likely caused by:
    hardware failure, congestion, configuration error, or a security incident.
    Output is a normalized probability distribution across all four,
    since real incidents are rarely 100% one cause.
    """

    def classify(self, signals: IncidentSignals) -> IncidentClassification:
        hardware_score = MIN_SCORE_FLOOR + (
            signals.failure_risk * HARDWARE_FAILURE_RISK_WEIGHT
            + signals.packet_loss_percent * HARDWARE_PACKET_LOSS_WEIGHT
        )

        congestion_score = MIN_SCORE_FLOOR + (
            max(0.0, signals.traffic_ratio - 1.0) * CONGESTION_TRAFFIC_WEIGHT
            + signals.latency_ms * CONGESTION_LATENCY_WEIGHT
        )

        configuration_score = MIN_SCORE_FLOOR + (
            CONFIG_CHANGE_SCORE if signals.recent_config_change else CONFIG_BASELINE_SCORE
        )

        security_score = MIN_SCORE_FLOOR + (signals.security_risk * SECURITY_RISK_WEIGHT)

        total = hardware_score + congestion_score + configuration_score + security_score

        return IncidentClassification(
            entity_id=signals.entity_id,
            hardware_failure=round(hardware_score / total, 4),
            congestion=round(congestion_score / total, 4),
            configuration_error=round(configuration_score / total, 4),
            security_incident=round(security_score / total, 4),
        )