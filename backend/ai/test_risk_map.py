"""
backend/ai/test_risk_map.py
Run with: pytest backend/ai/test_risk_map.py -v
"""

from backend.ai.anomaly_detection import detect_link_anomalies
from backend.ai.risk_map import generate_risk_map
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _pred(node_id, prob, trend="stable", eta=None):
    return {"node_id": node_id, "failure_probability": prob, "trend": trend,
            "estimated_ticks_to_failure": eta, "confidence": 0.8}


def test_node_and_edge_counts_match_topology():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=1)
    risk_map = generate_risk_map(gen.topology, [], [], gen.central_node_id)
    assert len(risk_map["nodes"]) == 5
    assert len(risk_map["edges"]) == 4


def test_node_with_no_prediction_defaults_to_none_severity():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    risk_map = generate_risk_map(gen.topology, [], [], gen.central_node_id)
    for n in risk_map["nodes"]:
        assert n["failure_probability"] == 0.0
        assert n["risk_severity"] == "none"
    assert risk_map["highest_risk_node"] is None


def test_high_risk_node_gets_critical_color():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=3)
    predictions = [_pred("leaf-0", 0.95, trend="worsening", eta=2)]
    risk_map = generate_risk_map(gen.topology, predictions, [], gen.central_node_id)
    leaf0 = next(n for n in risk_map["nodes"] if n["id"] == "leaf-0")
    assert leaf0["risk_severity"] == "critical"
    assert leaf0["color"] == "#8e0000"
    assert leaf0["trend"] == "worsening"
    assert leaf0["estimated_ticks_to_failure"] == 2


def test_highest_risk_node_identified_correctly():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    predictions = [_pred("leaf-0", 0.3), _pred("leaf-1", 0.9), _pred("leaf-2", 0.5)]
    risk_map = generate_risk_map(gen.topology, predictions, [], gen.central_node_id)
    assert risk_map["highest_risk_node"] == "leaf-1"


def test_central_node_at_origin():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=5)
    risk_map = generate_risk_map(gen.topology, [], [], gen.central_node_id)
    central = next(n for n in risk_map["nodes"] if n["is_central"])
    assert central["x"] == 0.0 and central["y"] == 0.0


def test_link_down_reflected_in_edges():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=6)
    target_link = gen.topology.links[0].link_id
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_DOWN, anomaly_target=target_link)
    link_results = detect_link_anomalies(snap)

    risk_map = generate_risk_map(gen.topology, [], link_results, gen.central_node_id)
    down_edge = next(e for e in risk_map["edges"] if e["id"] == target_link)
    assert down_edge["status"] == "down"
    others = [e for e in risk_map["edges"] if e["id"] != target_link]
    assert all(e["status"] == "up" for e in others)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")