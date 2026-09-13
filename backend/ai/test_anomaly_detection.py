"""
backend/ai/test_anomaly_detection.py
Run with: pytest backend/ai/test_anomaly_detection.py -v
"""

from backend.ai.anomaly_detection import (
    AnomalyDetector,
    LinkAnomalyDetector,
    Severity,
    detect_anomalies,
    detect_link_anomalies,
)
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _node_result(results, node_id):
    return next(r for r in results if r["node_id"] == node_id)


def _link_result(results, link_id):
    return next(r for r in results if r["link_id"] == link_id)


def test_normal_snapshot_has_no_node_anomalies():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=1)
    snap = gen.generate_snapshot()
    results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    assert len(results) == 6
    assert all(not r["is_anomalous"] for r in results)
    assert all(r["severity"] == Severity.NONE.value for r in results)


def test_normal_snapshot_has_no_link_anomalies():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=1)
    snap = gen.generate_snapshot()
    results = detect_link_anomalies(snap)
    assert len(results) == 5
    assert all(not r["is_anomalous"] for r in results)


def test_node_down_is_critical():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-2")
    results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    down = _node_result(results, "leaf-2")
    assert down["is_anomalous"] is True
    assert down["severity"] == Severity.CRITICAL.value
    assert "status=down" in down["reasons"]


def test_node_overload_flagged():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=3)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_OVERLOAD, anomaly_target="leaf-1")
    results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    flagged = _node_result(results, "leaf-1")
    assert flagged["is_anomalous"] is True
    assert any("cpu_util_pct" in r or "mem_util_pct" in r for r in flagged["reasons"])


def test_latency_spike_flagged_on_correct_node_only():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=4)
    snap = gen.generate_snapshot(anomaly=AnomalyType.LATENCY_SPIKE, anomaly_target="leaf-1")
    results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    flagged = _node_result(results, "leaf-1")
    assert flagged["is_anomalous"] is True
    others = [r for r in results if r["node_id"] != "leaf-1"]
    assert all(not r["is_anomalous"] for r in others)


def test_packet_loss_flagged():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=5)
    snap = gen.generate_snapshot(anomaly=AnomalyType.PACKET_LOSS, anomaly_target="leaf-3")
    results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    flagged = _node_result(results, "leaf-3")
    assert flagged["is_anomalous"] is True
    assert any(r.startswith("packet_loss_pct") for r in flagged["reasons"])


def test_link_down_is_critical_and_node_untouched():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=6)
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_DOWN, anomaly_target="central<->leaf-4")
    link_results = detect_link_anomalies(snap)
    down_link = _link_result(link_results, "central<->leaf-4")
    assert down_link["is_anomalous"] is True
    assert down_link["severity"] == Severity.CRITICAL.value

    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    leaf4_node = _node_result(node_results, "leaf-4")
    assert leaf4_node["is_anomalous"] is False  # this is the point of the split


def test_link_congestion_flagged():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=7)
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_CONGESTION, anomaly_target="central<->leaf-2")
    results = detect_link_anomalies(snap)
    flagged = _link_result(results, "central<->leaf-2")
    assert flagged["is_anomalous"] is True
    assert any(r.startswith("utilization_pct") for r in flagged["reasons"])


def test_central_node_uses_central_thresholds():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=8)
    snap = gen.generate_snapshot()
    for n in snap.nodes:
        if n.node_id == gen.central_node_id:
            n.latency_ms = 25.0
    results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    central_result = _node_result(results, gen.central_node_id)
    assert central_result["is_anomalous"] is True


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")