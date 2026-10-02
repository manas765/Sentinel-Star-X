"""
backend/ai/test_adaptive_thresholds.py
Run with: pytest backend/ai/test_adaptive_thresholds.py -v
"""

from backend.ai.adaptive_thresholds import AdaptiveThresholdManager
from backend.ai.anomaly_detection import (
    LinkAnomalyDetector,
    ThresholdAnomalyDetector,
    detect_anomalies,
    detect_link_anomalies,
)
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _feed_clean_ticks(manager, gen, count):
    for _ in range(count):
        snap = gen.generate_snapshot()
        node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
        link_results = detect_link_anomalies(snap)
        manager.update(snap, node_results, link_results, gen.central_node_id)


def test_not_ready_before_min_samples():
    manager = AdaptiveThresholdManager(min_samples=20)
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    _feed_clean_ticks(manager, gen, 5)
    assert manager.ready() is False
    cfg = manager.get_node_threshold_config()
    assert cfg.leaf_max_latency_ms == 10.0


def test_ready_after_enough_samples():
    manager = AdaptiveThresholdManager(min_samples=20)
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    _feed_clean_ticks(manager, gen, 25)
    assert manager.ready() is True


def test_computed_thresholds_reflect_observed_data_not_just_floor():
    manager = AdaptiveThresholdManager(min_samples=20, k=4.0)
    gen = SyntheticTelemetryGenerator(num_leaves=5, seed=3)
    _feed_clean_ticks(manager, gen, 50)
    cfg = manager.get_node_threshold_config()
    assert cfg.leaf_max_latency_ms > 15.0
    assert cfg.leaf_max_latency_ms < 60.0


def test_anomalous_ticks_excluded_from_baseline():
    manager = AdaptiveThresholdManager(min_samples=20, k=4.0)
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=4)
    _feed_clean_ticks(manager, gen, 40)
    baseline_cfg = manager.get_node_threshold_config()

    for snap in gen.stream(ticks=20, anomaly_at=0, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-0"):
        node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
        link_results = detect_link_anomalies(snap)
        manager.update(snap, node_results, link_results, gen.central_node_id)

    after_cfg = manager.get_node_threshold_config()
    assert abs(after_cfg.leaf_max_latency_ms - baseline_cfg.leaf_max_latency_ms) < 5.0


def test_computed_config_plugs_into_detectors_without_changes():
    manager = AdaptiveThresholdManager(min_samples=20)
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=5)
    _feed_clean_ticks(manager, gen, 30)

    node_cfg = manager.get_node_threshold_config()
    link_cfg = manager.get_link_threshold_config()
    adaptive_node_detector = ThresholdAnomalyDetector(config=node_cfg)
    adaptive_link_detector = LinkAnomalyDetector(config=link_cfg)

    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1")
    results = detect_anomalies(snap, central_node_id=gen.central_node_id, detector=adaptive_node_detector)
    leaf1 = next(r for r in results if r["node_id"] == "leaf-1")
    assert leaf1["is_anomalous"] is True

    snap2 = gen.generate_snapshot()
    link_results = detect_link_anomalies(snap2, detector=adaptive_link_detector)
    assert all(not r["is_anomalous"] for r in link_results)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")