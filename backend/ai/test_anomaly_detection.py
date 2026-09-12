"""
backend/ai/test_anomaly_detection.py

Run with: pytest backend/ai/test_anomaly_detection.py -v
"""

from backend.ai.anomaly_detection import (
    AnomalyDetector,
    Severity,
    ThresholdAnomalyDetector,
    detect_anomalies,
)
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _result(results, node_id):
    return next(r for r in results if r["node_id"] == node_id)


def test_normal_snapshot_has_no_anomalies():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=1)
    snapshot = gen.generate_snapshot()
    results = detect_anomalies(snapshot)
    assert len(results) == 6
    assert all(not r["is_anomalous"] for r in results)
    assert all(r["severity"] == Severity.NONE.value for r in results)


def test_node_down_is_critical():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=2)
    snapshot = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_node="leaf-2")
    results = detect_anomalies(snapshot)
    down = _result(results, "leaf-2")
    assert down["is_anomalous"] is True
    assert down["severity"] == Severity.CRITICAL.value
    assert "status=down" in down["reasons"]


def test_latency_spike_flagged_on_correct_node_only():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=3)
    snapshot = gen.generate_snapshot(anomaly=AnomalyType.LATENCY_SPIKE, anomaly_node="leaf-1")
    results = detect_anomalies(snapshot)
    flagged = _result(results, "leaf-1")
    assert flagged["is_anomalous"] is True

    others = [r for r in results if r["node_id"] != "leaf-1"]
    assert all(not r["is_anomalous"] for r in others)


def test_packet_loss_flagged():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=4)
    snapshot = gen.generate_snapshot(anomaly=AnomalyType.PACKET_LOSS, anomaly_node="leaf-3")
    results = detect_anomalies(snapshot)
    flagged = _result(results, "leaf-3")
    assert flagged["is_anomalous"] is True
    assert any("packet_loss_pct" in r for r in flagged["reasons"])


def test_congestion_flagged():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=5)
    snapshot = gen.generate_snapshot(anomaly=AnomalyType.CONGESTION, anomaly_node="leaf-4")
    results = detect_anomalies(snapshot)
    flagged = _result(results, "leaf-4")
    assert flagged["is_anomalous"] is True
    assert any(("traffic_mbps" in r) or ("bandwidth_mbps" in r) for r in flagged["reasons"])


def test_central_overload_flagged_on_central_node():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=6)
    snapshot = gen.generate_snapshot(anomaly=AnomalyType.CENTRAL_OVERLOAD, anomaly_node="central")
    results = detect_anomalies(snapshot)
    central = _result(results, "central")
    assert central["is_anomalous"] is True
    assert central["severity"] in (
        Severity.MEDIUM.value,
        Severity.HIGH.value,
        Severity.CRITICAL.value,
    )


def test_custom_detector_instance_works_via_convenience_function():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=7)
    snapshot = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_node="leaf-0")
    detector = ThresholdAnomalyDetector()
    results = detect_anomalies(snapshot, detector=detector)
    assert _result(results, "leaf-0")["is_anomalous"] is True


def test_active_detector_alias_matches_threshold_detector():
    assert AnomalyDetector is ThresholdAnomalyDetector


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")