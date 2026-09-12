"""
backend/ai/test_telemetry_sim.py

Run with: pytest backend/ai/test_telemetry_sim.py -v
"""

from backend.ai.telemetry_sim import (
    AnomalyType,
    NodeStatus,
    SyntheticTelemetryGenerator,
)


def test_snapshot_shape():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=1)
    snap = gen.generate_snapshot()
    assert len(snap) == 6  # 1 central + 5 leaves
    central = next(n for n in snap if n["is_central"])
    assert central["node_id"] == "central"
    for n in snap:
        assert n["status"] == NodeStatus.UP.value
        assert 0 <= n["packet_loss_pct"] <= 100


def test_reproducible_with_seed():
    gen1 = SyntheticTelemetryGenerator(num_leaves=4, seed=42)
    gen2 = SyntheticTelemetryGenerator(num_leaves=4, seed=42)
    assert gen1.generate_snapshot(ts=0) == gen2.generate_snapshot(ts=0)


def test_node_down_anomaly():
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_node="leaf-2")
    target = next(n for n in snap if n["node_id"] == "leaf-2")
    assert target["status"] == NodeStatus.DOWN.value
    assert target["packet_loss_pct"] == 100.0
    others = [n for n in snap if n["node_id"] != "leaf-2"]
    assert all(n["status"] == NodeStatus.UP.value for n in others)


def test_latency_spike_anomaly():
    gen_base = SyntheticTelemetryGenerator(num_leaves=5, seed=3)
    baseline = gen_base.generate_snapshot(ts=0)
    base_latency = next(n for n in baseline if n["node_id"] == "leaf-1")["latency_ms"]

    gen_spike = SyntheticTelemetryGenerator(num_leaves=5, seed=3)
    spiked = gen_spike.generate_snapshot(
        anomaly=AnomalyType.LATENCY_SPIKE, anomaly_node="leaf-1", ts=0
    )
    spiked_latency = next(n for n in spiked if n["node_id"] == "leaf-1")["latency_ms"]

    assert spiked_latency > base_latency * 5


def test_stream_yields_ticks_and_applies_anomaly_after_threshold():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=7)
    ticks = list(
        gen.stream(ticks=10, anomaly_at=5, anomaly=AnomalyType.NODE_DOWN, anomaly_node="leaf-0")
    )
    assert len(ticks) == 10

    pre = next(n for n in ticks[4] if n["node_id"] == "leaf-0")
    post = next(n for n in ticks[5] if n["node_id"] == "leaf-0")
    assert pre["status"] == NodeStatus.UP.value
    assert post["status"] == NodeStatus.DOWN.value


if __name__ == "__main__":
    # Lets this file double as a no-pytest smoke test:
    # `python backend/ai/test_telemetry_sim.py`
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")