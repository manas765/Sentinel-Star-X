"""
backend/ai/test_resilience_index.py
Run with: pytest backend/ai/test_resilience_index.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.resilience_index import calculate_resilience_index
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _none_node(node_id):
    return {"node_id": node_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}


def _anomalous_node(node_id, severity, reasons):
    return {"node_id": node_id, "is_anomalous": True, "score": 1.0, "severity": severity, "reasons": reasons}


def _none_link(link_id):
    return {"link_id": link_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}


def test_healthy_network_scores_100():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=1)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    report = calculate_resilience_index(node_results, link_results, [], gen.topology, gen.central_node_id)
    assert report["score"] == 100.0
    assert report["node_health"] == 1.0
    assert report["cascade_penalty"] == 0.0


def test_single_isolated_failure_scores_lower_than_healthy():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    node_results = [
        _anomalous_node("leaf-0", "critical", ["cpu_util_pct=95 > 85"]),
        _none_node("central"),
        _none_node("leaf-1"),
        _none_node("leaf-2"),
        _none_node("leaf-3"),
    ]
    link_results = [_none_link(l.link_id) for l in gen.topology.links]

    report = calculate_resilience_index(node_results, link_results, [], gen.topology, gen.central_node_id)
    assert report["score"] < 100.0
    assert report["score"] > 0.0


def test_central_cascade_scores_worse_than_isolated_failure_of_same_size():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=3)

    cascade_nodes = [_anomalous_node("central", "critical", ["status=down"])]
    cascade_nodes += [
        _anomalous_node(f"leaf-{i}", "medium", ["latency_ms=90 > 60"]) for i in range(4)
    ]
    cascade_links = [_none_link(l.link_id) for l in gen.topology.links]
    cascade_report = calculate_resilience_index(
        cascade_nodes, cascade_links, [], gen.topology, gen.central_node_id
    )

    independent_nodes = [_none_node("central")]
    independent_nodes += [
        _anomalous_node(f"leaf-{i}", "medium", ["cpu_util_pct=90 > 85"]) for i in range(4)
    ]
    independent_links = [_none_link(l.link_id) for l in gen.topology.links]
    independent_report = calculate_resilience_index(
        independent_nodes, independent_links, [], gen.topology, gen.central_node_id
    )

    assert cascade_report["cascade_penalty"] > independent_report["cascade_penalty"]
    assert cascade_report["score"] < independent_report["score"]


def test_high_prediction_risk_lowers_score_even_with_no_current_anomalies():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    predictions = [{"node_id": "leaf-0", "failure_probability": 0.9, "trend": "worsening",
                    "estimated_ticks_to_failure": 2, "confidence": 0.8}]

    report = calculate_resilience_index(
        node_results, link_results, predictions, gen.topology, gen.central_node_id
    )
    assert report["score"] < 100.0
    assert report["prediction_risk"] == 0.9


def test_score_always_between_0_and_100():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=5)
    worst_nodes = [_anomalous_node("central", "critical", ["status=down"])]
    worst_nodes += [_anomalous_node(f"leaf-{i}", "critical", ["status=down"]) for i in range(3)]
    worst_links = [_none_link(l.link_id) for l in gen.topology.links]
    predictions = [
        {"node_id": f"leaf-{i}", "failure_probability": 1.0, "trend": "worsening",
         "estimated_ticks_to_failure": 1, "confidence": 1.0}
        for i in range(3)
    ]
    report = calculate_resilience_index(
        worst_nodes, worst_links, predictions, gen.topology, gen.central_node_id
    )
    assert 0.0 <= report["score"] <= 100.0


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")