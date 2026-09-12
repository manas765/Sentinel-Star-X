"""
backend/ai/test_failure_prediction.py

Run with: pytest backend/ai/test_failure_prediction.py -v
"""

from collections import deque

from backend.ai.failure_prediction import TrendFailurePredictor, predict_failures
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def test_not_enough_history_returns_stable_no_eta():
    predictor = TrendFailurePredictor(window_size=10)
    predictor.update(
        [
            {
                "node_id": "leaf-0",
                "is_central": False,
                "status": "up",
                "latency_ms": 10,
                "packet_loss_pct": 0.1,
                "bandwidth_mbps": 90,
                "traffic_in_mbps": 10,
                "traffic_out_mbps": 10,
            }
        ]
    )
    results = predict_failures(predictor)
    r = next(x for x in results if x["node_id"] == "leaf-0")
    assert r["trend"] == "stable"
    assert r["estimated_ticks_to_failure"] is None
    assert r["confidence"] == 0.0


def test_rising_scores_detected_as_worsening_with_eta():
    predictor = TrendFailurePredictor(window_size=10, failure_threshold=0.85)
    predictor._history["leaf-1"] = deque([0.1, 0.2, 0.3, 0.4, 0.5], maxlen=10)
    results = predictor.predict()
    r = next(x for x in results if x.node_id == "leaf-1")
    assert r.trend == "worsening"
    assert r.estimated_ticks_to_failure is not None
    assert r.estimated_ticks_to_failure > 0


def test_falling_scores_detected_as_improving():
    predictor = TrendFailurePredictor(window_size=10)
    predictor._history["leaf-2"] = deque([0.8, 0.6, 0.4, 0.2], maxlen=10)
    results = predictor.predict()
    r = next(x for x in results if x.node_id == "leaf-2")
    assert r.trend == "improving"
    assert r.estimated_ticks_to_failure is None  # not heading toward failure


def test_flat_scores_detected_as_stable():
    predictor = TrendFailurePredictor(window_size=10)
    predictor._history["leaf-3"] = deque([0.3, 0.31, 0.29, 0.3], maxlen=10)
    results = predictor.predict()
    r = next(x for x in results if x.node_id == "leaf-3")
    assert r.trend == "stable"


def test_already_failed_node_has_no_eta_and_high_probability():
    predictor = TrendFailurePredictor(window_size=10, failure_threshold=0.85)
    predictor._history["leaf-4"] = deque([0.9, 0.95, 1.0, 1.0], maxlen=10)
    results = predictor.predict()
    r = next(x for x in results if x.node_id == "leaf-4")
    assert r.failure_probability >= 0.85
    assert r.estimated_ticks_to_failure is None  # already at/over threshold


def test_integration_with_generator_and_detector_stream():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=11)
    predictor = TrendFailurePredictor(window_size=10)
    for snapshot in gen.stream(
        ticks=8, anomaly_at=4, anomaly=AnomalyType.NODE_DOWN, anomaly_node="leaf-0"
    ):
        predictor.update(snapshot)

    results = predict_failures(predictor)
    r = next(x for x in results if x["node_id"] == "leaf-0")
    assert r["failure_probability"] > 0.5


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")