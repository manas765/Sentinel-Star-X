"""
backend/ai/test_failure_classification.py
Run with: pytest backend/ai/test_failure_classification.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.failure_classification import (
    FailureCategory,
    classify_failures,
    classify_link_failures,
)
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _classify_node_for(anomaly_type, target="leaf-1", num_leaves=5, seed=1):
    gen = SyntheticTelemetryGenerator(num_leaves=num_leaves, seed=seed)
    snap = gen.generate_snapshot(anomaly=anomaly_type, anomaly_target=target)
    anomalies = detect_anomalies(snap, central_node_id=gen.central_node_id)
    classified = classify_failures(anomalies)
    return next(c for c in classified if c["node_id"] == target)


def _classify_link_for(anomaly_type, target, num_leaves=5, seed=1):
    gen = SyntheticTelemetryGenerator(num_leaves=num_leaves, seed=seed)
    snap = gen.generate_snapshot(anomaly=anomaly_type, anomaly_target=target)
    link_anomalies = detect_link_anomalies(snap)
    classified = classify_link_failures(link_anomalies)
    return next(c for c in classified if c["link_id"] == target)


def test_normal_node_classified_none():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    snap = gen.generate_snapshot()
    anomalies = detect_anomalies(snap, central_node_id=gen.central_node_id)
    classified = classify_failures(anomalies)
    assert all(c["category"] == FailureCategory.NONE.value for c in classified)


def test_node_down_classified_correctly():
    result = _classify_node_for(AnomalyType.NODE_DOWN, target="leaf-2", seed=3)
    assert result["category"] == FailureCategory.NODE_DOWN.value
    assert result["possible_security"] is False


def test_node_overload_classified_correctly():
    result = _classify_node_for(AnomalyType.NODE_OVERLOAD, target="leaf-1", seed=4)
    assert result["category"] == FailureCategory.NODE_OVERLOAD.value


def test_latency_spike_classified_correctly():
    result = _classify_node_for(AnomalyType.LATENCY_SPIKE, target="leaf-1", seed=5)
    assert result["category"] == FailureCategory.LATENCY_DEGRADATION.value


def test_packet_loss_classified_correctly():
    result = _classify_node_for(AnomalyType.PACKET_LOSS, target="leaf-3", seed=6)
    assert result["category"] == FailureCategory.PACKET_LOSS.value


def test_link_down_classified_correctly():
    result = _classify_link_for(AnomalyType.LINK_DOWN, target="central<->leaf-2", seed=7)
    assert result["category"] == FailureCategory.LINK_DOWN.value


def test_link_congestion_classified_correctly():
    result = _classify_link_for(AnomalyType.LINK_CONGESTION, target="central<->leaf-3", seed=8)
    assert result["category"] == FailureCategory.LINK_CONGESTION.value


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")