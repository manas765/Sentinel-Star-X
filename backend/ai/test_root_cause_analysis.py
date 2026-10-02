"""
backend/ai/test_root_cause_analysis.py
Run with: pytest backend/ai/test_root_cause_analysis.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _none_node(node_id):
    return {"node_id": node_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}


def _anomalous_node(node_id, score, severity, reasons):
    return {"node_id": node_id, "is_anomalous": True, "score": score, "severity": severity, "reasons": reasons}


def _none_link(link_id):
    return {"link_id": link_id, "is_anomalous": False, "score": 0.0, "severity": "none", "reasons": []}


def _anomalous_link(link_id, score, severity, reasons):
    return {"link_id": link_id, "is_anomalous": True, "score": score, "severity": severity, "reasons": reasons}


def test_central_failure_groups_leaves_as_symptoms():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    node_anomalies = [
        _anomalous_node("central", 1.0, "critical", ["status=down"]),
        _anomalous_node("leaf-0", 0.4, "medium", ["latency_ms=80 > 60"]),
        _anomalous_node("leaf-1", 0.4, "medium", ["packet_loss_pct=10 > 5"]),
        _none_node("leaf-2"),
    ]
    link_anomalies = [_none_link(l.link_id) for l in gen.topology.links]

    results = analyze_root_causes(node_anomalies, link_anomalies, gen.topology, gen.central_node_id)
    assert len(results) == 1
    root = results[0]
    assert root["root_cause_id"] == "central"
    assert set(root["affected_nodes"]) == {"leaf-0", "leaf-1"}


def test_link_failure_explains_leaf_symptom():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    target_link = next(l.link_id for l in gen.topology.links if l.target_id == "leaf-1")

    node_anomalies = [
        _none_node("central"),
        _none_node("leaf-0"),
        _anomalous_node("leaf-1", 0.3, "medium", ["packet_loss_pct=12 > 5"]),
        _none_node("leaf-2"),
    ]
    link_anomalies = [
        _anomalous_link(l.link_id, 0.9, "critical", ["status=down"])
        if l.link_id == target_link
        else _none_link(l.link_id)
        for l in gen.topology.links
    ]

    results = analyze_root_causes(node_anomalies, link_anomalies, gen.topology, gen.central_node_id)
    assert len(results) == 1
    root = results[0]
    assert root["root_cause_type"] == "link"
    assert root["root_cause_id"] == target_link
    assert root["affected_nodes"] == ["leaf-1"]


def test_resource_based_node_anomaly_not_merged_with_coincidental_link_anomaly():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=3)
    target_link = next(l.link_id for l in gen.topology.links if l.target_id == "leaf-0")

    node_anomalies = [
        _none_node("central"),
        _anomalous_node("leaf-0", 0.6, "high", ["cpu_util_pct=95 > 85"]),
        _none_node("leaf-1"),
        _none_node("leaf-2"),
    ]
    link_anomalies = [
        _anomalous_link(l.link_id, 0.7, "high", ["utilization_pct=95 > 85"])
        if l.link_id == target_link
        else _none_link(l.link_id)
        for l in gen.topology.links
    ]

    results = analyze_root_causes(node_anomalies, link_anomalies, gen.topology, gen.central_node_id)
    assert len(results) == 2  # kept separate, not merged
    ids = {(r["root_cause_type"], r["root_cause_id"]) for r in results}
    assert ("node", "leaf-0") in ids
    assert ("link", target_link) in ids


def test_unrelated_independent_anomalies_stay_separate():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    node_anomalies = [
        _none_node("central"),
        _anomalous_node("leaf-0", 0.5, "medium", ["cpu_util_pct=90 > 85"]),
        _anomalous_node("leaf-1", 0.5, "medium", ["mem_util_pct=92 > 85"]),
        _none_node("leaf-2"),
    ]
    link_anomalies = [_none_link(l.link_id) for l in gen.topology.links]

    results = analyze_root_causes(node_anomalies, link_anomalies, gen.topology, gen.central_node_id)
    assert len(results) == 2
    ids = {r["root_cause_id"] for r in results}
    assert ids == {"leaf-0", "leaf-1"}
    assert all(r["affected_nodes"] == [] and r["affected_links"] == [] for r in results)


def test_integration_central_node_down_via_real_pipeline():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=5)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target=gen.central_node_id)
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    results = analyze_root_causes(node_results, link_results, gen.topology, gen.central_node_id)
    assert len(results) == 1
    assert results[0]["root_cause_id"] == gen.central_node_id
    assert results[0]["root_cause_type"] == "node"


def test_no_anomalies_returns_empty_list():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=6)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    results = analyze_root_causes(node_results, link_results, gen.topology, gen.central_node_id)
    assert results == []


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")