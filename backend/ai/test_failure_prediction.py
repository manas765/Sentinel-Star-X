"""
backend/ai/test_failure_prediction.py
Run with: pytest backend/ai/test_failure_prediction.py -v
"""

from collections import deque

from backend.ai.failure_prediction import TrendFailurePredictor, get_failure_risk, predict_failures
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def test_not_enough_history_returns_stable_no_eta():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    predictor = TrendFailurePredictor(central_node_id=gen.central_node_id, window_size=10)
    predictor.update(gen.generate_snapshot())
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
    assert r.estimated_ticks_to_failure is None


def test_already_failed_node_has_no_eta_and_high_probability():
    predictor = TrendFailurePredictor(window_size=10, failure_threshold=0.85)
    predictor._history["leaf-4"] = deque([0.9, 0.95, 1.0, 1.0], maxlen=10)
    results = predictor.predict()
    r = next(x for x in results if x.node_id == "leaf-4")
    assert r.failure_probability >= 0.85
    assert r.estimated_ticks_to_failure is None


def test_integration_with_generator_and_detector_stream():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=11)
    predictor = TrendFailurePredictor(central_node_id=gen.central_node_id, window_size=10)
    for snap in gen.stream(ticks=8, anomaly_at=4, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-0"):
        predictor.update(snap)

    results = predict_failures(predictor)
    r = next(x for x in results if x["node_id"] == "leaf-0")
    assert r["failure_probability"] > 0.5


def test_get_failure_risk_returns_probability_for_known_node():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=12)
    predictor = TrendFailurePredictor(central_node_id=gen.central_node_id, window_size=10)
    for snap in gen.stream(ticks=6, anomaly_at=3, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1"):
        predictor.update(snap)

    risk = get_failure_risk(predictor, "leaf-1")
    assert 0.0 <= risk <= 1.0
    assert risk > 0.3  # node has been down for several ticks


def test_get_failure_risk_returns_zero_for_unknown_node():
    predictor = TrendFailurePredictor(window_size=10)
    assert get_failure_risk(predictor, "nonexistent-node") == 0.0


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")