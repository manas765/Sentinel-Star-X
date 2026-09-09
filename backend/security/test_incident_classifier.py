from security.incident_classifier import FailureVsSecurityClassifier
from security.incident_models import IncidentSignals


def test_high_security_risk_dominates():
    classifier = FailureVsSecurityClassifier()
    signals = IncidentSignals(
        entity_id="PC-20",
        security_risk=0.9,
        failure_risk=0.05,
        packet_loss_percent=0.5,
        latency_ms=10.0,
        traffic_ratio=1.1,
    )
    result = classifier.classify(signals)
    assert result.probable_cause == "security_incident"
    assert result.security_incident > 0.5


def test_recent_config_change_dominates():
    classifier = FailureVsSecurityClassifier()
    signals = IncidentSignals(
        entity_id="PC-21",
        security_risk=0.05,
        failure_risk=0.05,
        packet_loss_percent=0.2,
        latency_ms=15.0,
        traffic_ratio=1.0,
        recent_config_change=True,
    )
    result = classifier.classify(signals)
    assert result.probable_cause == "configuration_error"


def test_high_traffic_and_latency_indicates_congestion():
    classifier = FailureVsSecurityClassifier()
    signals = IncidentSignals(
        entity_id="PC-22",
        security_risk=0.05,
        failure_risk=0.05,
        packet_loss_percent=1.0,
        latency_ms=180.0,
        traffic_ratio=4.0,
    )
    result = classifier.classify(signals)
    assert result.probable_cause == "congestion"


def test_high_failure_risk_indicates_hardware():
    classifier = FailureVsSecurityClassifier()
    signals = IncidentSignals(
        entity_id="PC-23",
        security_risk=0.05,
        failure_risk=0.85,
        packet_loss_percent=6.0,
        latency_ms=20.0,
        traffic_ratio=1.0,
    )
    result = classifier.classify(signals)
    assert result.probable_cause == "hardware_failure"


def test_probabilities_sum_to_one():
    classifier = FailureVsSecurityClassifier()
    signals = IncidentSignals(entity_id="PC-24", security_risk=0.3, failure_risk=0.3)
    result = classifier.classify(signals)
    total = (
        result.hardware_failure
        + result.congestion
        + result.configuration_error
        + result.security_incident
    )
    assert abs(total - 1.0) < 0.01