"""
backend/ai/test_uncertainty_aware_decisions.py
Run with: pytest backend/ai/test_uncertainty_aware_decisions.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator
from backend.ai.uncertainty_aware_decisions import AutonomyLevel, decide_autonomy


def test_healthy_target_gets_hold_zero_uncertainty():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    decisions = decide_autonomy(node_results, link_results, gen.topology, gen.central_node_id)
    assert all(d["autonomy_level"] == AutonomyLevel.HOLD.value for d in decisions)
    assert all(d["uncertainty_score"] == 0.0 for d in decisions)


def test_isolated_node_down_is_autonomous():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1")
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    decisions = decide_autonomy(node_results, link_results, gen.topology, gen.central_node_id)
    leaf1 = next(d for d in decisions if d["target_id"] == "leaf-1")
    assert leaf1["autonomy_level"] == AutonomyLevel.AUTONOMOUS.value
    assert leaf1["uncertainty_score"] < 0.15


def test_symptom_always_requires_approval_never_autonomous():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=3)
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

    decisions = decide_autonomy(node_results, link_results, gen.topology, gen.central_node_id)
    leaf0 = next(d for d in decisions if d["target_id"] == "leaf-0")
    assert leaf0["autonomy_level"] == AutonomyLevel.REQUIRES_APPROVAL.value

    central = next(d for d in decisions if d["target_id"] == "central")
    assert central["autonomy_level"] == AutonomyLevel.AUTONOMOUS.value


def test_high_confidence_non_critical_gets_autonomous_notify():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    node_results = [
        {"node_id": "leaf-0", "is_anomalous": True, "score": 0.95, "severity": "high", "reasons": ["packet_loss_pct=40 > 5"]},
        {"node_id": "central", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
        {"node_id": "leaf-1", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
        {"node_id": "leaf-2", "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []},
    ]
    link_results = [
        {"link_id": l.link_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}
        for l in gen.topology.links
    ]
    decisions = decide_autonomy(node_results, link_results, gen.topology, gen.central_node_id)
    leaf0 = next(d for d in decisions if d["target_id"] == "leaf-0")
    assert leaf0["autonomy_level"] == AutonomyLevel.AUTONOMOUS_NOTIFY.value


def test_possible_security_pattern_never_autonomous():
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
    decisions = decide_autonomy(node_results, link_results, gen.topology, gen.central_node_id)
    leaf0 = next(d for d in decisions if d["target_id"] == "leaf-0")
    assert leaf0["autonomy_level"] != AutonomyLevel.AUTONOMOUS.value


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")