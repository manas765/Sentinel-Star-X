"""
backend/ai/test_graph_generation.py
Run with: pytest backend/ai/test_graph_generation.py -v
"""

import math

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.graph_generation import generate_graph
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def test_node_and_edge_counts_match_topology():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=1)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id)
    assert len(graph["nodes"]) == 6
    assert len(graph["edges"]) == 5


def test_central_node_positioned_at_origin():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id)
    central = next(n for n in graph["nodes"] if n["id"] == gen.central_node_id)
    assert central["x"] == 0.0
    assert central["y"] == 0.0
    assert central["is_central"] is True


def test_leaf_nodes_positioned_at_radius():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=3)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id, radius=300.0)
    for n in graph["nodes"]:
        if not n["is_central"]:
            dist = math.hypot(n["x"], n["y"])
            assert abs(dist - 300.0) < 0.5


def test_healthy_node_is_green_and_up():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id)
    for n in graph["nodes"]:
        assert n["status"] == "up"
        assert n["severity"] == "none"
        assert n["color"] == "#2ecc71"


def test_node_down_reflected_in_graph():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=5)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1")
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id)
    leaf1 = next(n for n in graph["nodes"] if n["id"] == "leaf-1")
    assert leaf1["status"] == "down"
    assert leaf1["severity"] == "critical"
    assert leaf1["color"] == "#8e0000"
    assert leaf1["category"] == "node_down"

    others = [n for n in graph["nodes"] if n["id"] != "leaf-1"]
    assert all(n["status"] == "up" for n in others)


def test_link_down_reflected_in_graph():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=6)
    target_link = gen.topology.links[0].link_id
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_DOWN, anomaly_target=target_link)
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id)
    down_edge = next(e for e in graph["edges"] if e["id"] == target_link)
    assert down_edge["status"] == "down"
    assert down_edge["category"] == "link_down"

    others = [e for e in graph["edges"] if e["id"] != target_link]
    assert all(e["status"] == "up" for e in others)


def test_edges_reference_correct_source_and_target():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=7)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    graph = generate_graph(gen.topology, node_results, link_results, gen.central_node_id)
    topo_by_id = {l.link_id: l for l in gen.topology.links}
    for e in graph["edges"]:
        topo_link = topo_by_id[e["id"]]
        assert e["source"] == topo_link.source_id
        assert e["target"] == topo_link.target_id


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")