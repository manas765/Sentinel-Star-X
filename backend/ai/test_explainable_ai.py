"""
backend/ai/test_explainable_ai.py
Run with: pytest backend/ai/test_explainable_ai.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.explainable_ai import explain_network_state
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def test_healthy_node_gets_simple_healthy_summary():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    explanations = explain_network_state(node_results, link_results, gen.topology, gen.central_node_id)
    for e in explanations:
        assert "healthy" in e["summary"]
        assert e["details"] == []


def test_node_down_gets_readable_summary_and_details():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1")
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    explanations = explain_network_state(node_results, link_results, gen.topology, gen.central_node_id)
    leaf1 = next(e for e in explanations if e["target_id"] == "leaf-1")
    assert "unreachable" in leaf1["summary"]
    assert "critical" in leaf1["summary"]
    assert any("Classified as: node_down" in d for d in leaf1["details"])
    assert any("Confidence" in d for d in leaf1["details"])


def test_central_cascade_explains_symptoms_as_downstream():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=3)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target=gen.central_node_id)
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    explanations = explain_network_state(node_results, link_results, gen.topology, gen.central_node_id)
    central_exp = next(e for e in explanations if e["target_id"] == gen.central_node_id)
    assert central_exp["is_root_cause"] is True
    assert central_exp["is_symptom_of"] is None


def test_link_congestion_gets_readable_summary():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    target_link = gen.topology.links[0].link_id
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_CONGESTION, anomaly_target=target_link)
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    explanations = explain_network_state(node_results, link_results, gen.topology, gen.central_node_id)
    link_exp = next(e for e in explanations if e["target_id"] == target_link)
    assert link_exp["target_type"] == "link"
    assert "saturated" in link_exp["summary"]


def test_all_targets_get_an_explanation():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=5)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    explanations = explain_network_state(node_results, link_results, gen.topology, gen.central_node_id)
    assert len(explanations) == 6 + 5


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")