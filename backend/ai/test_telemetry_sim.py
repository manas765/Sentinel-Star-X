"""
backend/ai/test_telemetry_sim.py
Run with: pytest backend/ai/test_telemetry_sim.py -v
"""

from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator
from backend.telemetry.schema import LinkStatus, NodeStatus


def test_snapshot_shape():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=1)
    snap = gen.generate_snapshot()
    assert len(snap.nodes) == 6
    assert len(snap.links) == 5
    assert gen.central_node_id == "central"
    for n in snap.nodes:
        assert n.status == NodeStatus.UP
        assert 0 <= n.packet_loss_pct <= 100
    for l in snap.links:
        assert l.status == LinkStatus.UP


def test_topology_matches_generator():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=1)
    assert len(gen.topology.devices) == 5  # 1 central + 4 leaves
    assert len(gen.topology.links) == 4
    central_device = next(d for d in gen.topology.devices if d.node_id == "central")
    assert central_device.is_central is True


def test_reproducible_with_seed():
    gen1 = SyntheticTelemetryGenerator(num_leaves=4, seed=42)
    gen2 = SyntheticTelemetryGenerator(num_leaves=4, seed=42)
    assert gen1.generate_snapshot(ts=0).to_dict() == gen2.generate_snapshot(ts=0).to_dict()


def test_node_down_anomaly():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-2")
    target = next(n for n in snap.nodes if n.node_id == "leaf-2")
    assert target.status == NodeStatus.DOWN
    assert target.packet_loss_pct == 100.0
    others = [n for n in snap.nodes if n.node_id != "leaf-2"]
    assert all(n.status == NodeStatus.UP for n in others)


def test_link_down_anomaly_does_not_touch_nodes():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=3)
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_DOWN, anomaly_target="central<->leaf-1")
    target_link = next(l for l in snap.links if l.link_id == "central<->leaf-1")
    assert target_link.status == LinkStatus.DOWN
    assert target_link.packet_loss_pct == 100.0
    # this is the whole point of the split -- the node itself is untouched
    assert all(n.status == NodeStatus.UP for n in snap.nodes)


def test_link_congestion_anomaly():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=4)
    snap = gen.generate_snapshot(anomaly=AnomalyType.LINK_CONGESTION, anomaly_target="central<->leaf-3")
    target_link = next(l for l in snap.links if l.link_id == "central<->leaf-3")
    assert target_link.utilization_pct > 85


def test_stream_yields_ticks_and_applies_anomaly_after_threshold():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=7)
    ticks = list(
        gen.stream(ticks=10, anomaly_at=5, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-0")
    )
    assert len(ticks) == 10
    pre = next(n for n in ticks[4].nodes if n.node_id == "leaf-0")
    post = next(n for n in ticks[5].nodes if n.node_id == "leaf-0")
    assert pre.status == NodeStatus.UP
    assert post.status == NodeStatus.DOWN


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")