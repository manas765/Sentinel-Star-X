"""
backend/ai/test_recovery_confidence.py
Run with: pytest backend/ai/test_recovery_confidence.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.recovery_confidence import evaluate_recovery_confidence
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def test_healthy_targets_get_no_action_needed():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    results = evaluate_recovery_confidence(node_results, link_results, gen.topology, gen.central_node_id)
    assert all(r["recommendation"] == "no_action_needed" for r in results)
    assert all(r["recovery_confidence"] == 1.0 for r in results)


def test_isolated_node_down_recommends_act_here_with_high_confidence():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1")
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    results = evaluate_recovery_confidence(node_results, link_results, gen.topology, gen.central_node_id)
    leaf1 = next(r for r in results if r["target_id"] == "leaf-1")
    assert leaf1["recommendation"] == "act_here"
    assert leaf1["recovery_confidence"] >= 0.7
    assert leaf1["is_root_cause"] is True


def test_central_cascade_points_leaves_to_root_cause():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=3)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target=gen.central_node_id)
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    results = evaluate_recovery_confidence(node_results, link_results, gen.topology, gen.central_node_id)
    central_result = next(r for r in results if r["target_id"] == gen.central_node_id)
    assert central_result["recommendation"] == "act_here"
    assert central_result["is_root_cause"] is True


def test_symptom_target_points_to_root_cause_with_low_confidence():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)

    node_results = [
        {"node_id": "central", "is_anomalous": True, "score": 1.0, "severity": "critical", "reasons": ["status=down"]},
        {"node_id": "leaf-0", "is_anomalous": True, "score": 0.4, "severity": "medium", "reasons": ["latency_ms=80 > 60"]},
        {"node_id": "leaf-1", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
        {"node_id": "leaf-2", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
    ]
    link_results = [
        {"link_id": l.link_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}
        for l in gen.topology.links
    ]

    results = evaluate_recovery_confidence(node_results, link_results, gen.topology, gen.central_node_id)
    leaf0 = next(r for r in results if r["target_id"] == "leaf-0")
    assert leaf0["recommendation"] == "act_on_root_cause_instead"
    assert leaf0["points_to"] == "central"
    assert leaf0["recovery_confidence"] < 0.4


def test_possible_security_pattern_lowers_confidence():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=5)
    node_results = [
        {"node_id": "leaf-0", "is_anomalous": True, "score": 0.9, "severity": "high", "reasons": ["status=degraded"]},
        {"node_id": "central", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
        {"node_id": "leaf-1", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
        {"node_id": "leaf-2", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
    ]
    link_results = [
        {"link_id": l.link_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}
        for l in gen.topology.links
    ]

    results = evaluate_recovery_confidence(node_results, link_results, gen.topology, gen.central_node_id)
    leaf0 = next(r for r in results if r["target_id"] == "leaf-0")
    assert leaf0["recovery_confidence"] < 0.9


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")