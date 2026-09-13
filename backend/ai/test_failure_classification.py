"""
backend/ai/test_failure_classification.py

Run with: pytest backend/ai/test_failure_classification.py -v
"""

from backend.ai.anomaly_detection import AnomalyResult, Severity, detect_anomalies
from backend.ai.failure_classification import FailureCategory, classify_failures
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _classify_for_anomaly(anomaly_type, node="leaf-1", num_leaves=5, seed=1):
    gen = SyntheticTelemetryGenerator(num_leaves=num_leaves, seed=seed)
    snapshot = gen.generate_snapshot(anomaly=anomaly_type, anomaly_node=node)
    anomalies = detect_anomalies(snapshot)
    classified = classify_failures(anomalies)
    return next(c for c in classified if c["node_id"] == node)


def test_normal_node_classified_none():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    snapshot = gen.generate_snapshot()
    anomalies = detect_anomalies(snapshot)
    classified = classify_failures(anomalies)
    assert all(c["category"] == FailureCategory.NONE.value for c in classified)
    assert all(not c["possible_security"] for c in classified)


def test_node_down_classified_correctly():
    result = _classify_for_anomaly(AnomalyType.NODE_DOWN, node="leaf-2", seed=3)
    assert result["category"] == FailureCategory.NODE_DOWN.value
    assert result["possible_security"] is False


def test_latency_spike_classified_correctly():
    result = _classify_for_anomaly(AnomalyType.LATENCY_SPIKE, node="leaf-1", seed=4)
    assert result["category"] == FailureCategory.LATENCY_DEGRADATION.value


def test_packet_loss_classified_correctly():
    result = _classify_for_anomaly(AnomalyType.PACKET_LOSS, node="leaf-3", seed=5)
    assert result["category"] == FailureCategory.PACKET_LOSS.value


def test_congestion_classified_correctly():
    result = _classify_for_anomaly(AnomalyType.CONGESTION, node="leaf-4", seed=6)
    assert result["category"] == FailureCategory.CONGESTION.value


def test_central_overload_classified_correctly():
    result = _classify_for_anomaly(AnomalyType.CENTRAL_OVERLOAD, node="central", seed=7)
    assert result["category"] == FailureCategory.CENTRAL_OVERLOAD.value


def test_unclear_pattern_flagged_possible_security():
    # A degraded status with no metric explanation doesn't come out of the
    # synthetic generator's own anomaly types -- build it directly. This is
    # exactly the edge case meant to route to Manas's differentiator.
    weird = AnomalyResult(
        node_id="leaf-9",
        is_anomalous=True,
        score=0.5,
        severity=Severity.MEDIUM,
        reasons=["status=degraded"],
    )
    classified = classify_failures([weird])
    result = classified[0]
    assert result["category"] == FailureCategory.UNKNOWN.value
    assert result["possible_security"] is True


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")