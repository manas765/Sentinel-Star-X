from security.anomaly_detector import SecurityAnomalyDetector
from security.models import NetworkActivitySnapshot


def test_normal_activity_has_low_risk():
    detector = SecurityAnomalyDetector()
    snapshot = NetworkActivitySnapshot(
        entity_id="PC-10",
        traffic_volume_mbps=5.0,
        baseline_traffic_mbps=5.0,
        connection_count=3,
        baseline_connection_count=3,
        communicating_with=["SERVER-01"],
        authorized_peers=["SERVER-01"],
    )
    result = detector.assess(snapshot)
    assert result.risk_score == 0.0
    assert result.threat_level == "NORMAL"
    assert result.flags == []


def test_traffic_spike_raises_risk():
    detector = SecurityAnomalyDetector()
    snapshot = NetworkActivitySnapshot(
        entity_id="PC-11",
        traffic_volume_mbps=20.0,
        baseline_traffic_mbps=5.0,
        connection_count=3,
        baseline_connection_count=3,
    )
    result = detector.assess(snapshot)
    assert result.risk_score >= 0.3
    assert any("traffic spike" in f for f in result.flags)


def test_unexpected_peer_communication_flagged():
    detector = SecurityAnomalyDetector()
    snapshot = NetworkActivitySnapshot(
        entity_id="PC-12",
        traffic_volume_mbps=5.0,
        baseline_traffic_mbps=5.0,
        connection_count=3,
        baseline_connection_count=3,
        communicating_with=["DB-SERVER", "UNKNOWN-DEVICE"],
        authorized_peers=["DB-SERVER"],
    )
    result = detector.assess(snapshot)
    assert any("UNKNOWN-DEVICE" in f for f in result.flags)
    assert result.risk_score >= 0.25


def test_unauthorized_device_is_high_risk():
    detector = SecurityAnomalyDetector()
    snapshot = NetworkActivitySnapshot(
        entity_id="ROGUE-01",
        traffic_volume_mbps=5.0,
        baseline_traffic_mbps=5.0,
        connection_count=3,
        baseline_connection_count=3,
        is_authorized_device=False,
    )
    result = detector.assess(snapshot)
    assert result.risk_score >= 0.4


def test_multiple_flags_compound_to_critical():
    detector = SecurityAnomalyDetector()
    snapshot = NetworkActivitySnapshot(
        entity_id="ROGUE-02",
        traffic_volume_mbps=30.0,
        baseline_traffic_mbps=5.0,
        connection_count=20,
        baseline_connection_count=3,
        communicating_with=["UNKNOWN-1"],
        authorized_peers=[],
        failed_auth_attempts=5,
        is_authorized_device=False,
    )
    result = detector.assess(snapshot)
    assert result.risk_score == 1.0  # capped even though raw sum exceeds 1.0
    assert result.threat_level == "CRITICAL"