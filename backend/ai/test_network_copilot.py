"""
backend/ai/test_network_copilot.py
Run with: pytest backend/ai/test_network_copilot.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.failure_prediction import TrendFailurePredictor, predict_failures
from backend.ai.network_copilot import QueryIntent, ask_copilot
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def test_status_summary_healthy_network():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    response = ask_copilot(
        QueryIntent.STATUS_SUMMARY, node_results, link_results, [], gen.topology, gen.central_node_id
    )
    assert "healthy" in response["answer"]
    assert response["intent"] == "status_summary"


def test_whats_wrong_reports_problems():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-0")
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    response = ask_copilot(
        QueryIntent.WHATS_WRONG, node_results, link_results, [], gen.topology, gen.central_node_id
    )
    assert "leaf-0" in response["answer"]
    assert "unreachable" in response["answer"]


def test_whats_wrong_nothing_when_healthy():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=3)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    response = ask_copilot(
        QueryIntent.WHATS_WRONG, node_results, link_results, [], gen.topology, gen.central_node_id
    )
    assert "Nothing's wrong" in response["answer"]


def test_what_to_fix_first_isolated_failure():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=4)
    snap = gen.generate_snapshot(anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-2")
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    response = ask_copilot(
        QueryIntent.WHAT_TO_FIX_FIRST, node_results, link_results, [], gen.topology, gen.central_node_id
    )
    assert "leaf-2" in response["answer"]
    assert "act_here" in response["answer"]


def test_resilience_score_intent():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=5)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    response = ask_copilot(
        QueryIntent.RESILIENCE_SCORE, node_results, link_results, [], gen.topology, gen.central_node_id
    )
    assert "100.0/100" in response["answer"] or "Resilience index is" in response["answer"]


def test_forecast_intent():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=6)
    snap = gen.generate_snapshot()
    node_results = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(snap)

    response = ask_copilot(
        QueryIntent.FORECAST, node_results, link_results, [], gen.topology, gen.central_node_id, horizon_ticks=5
    )
    assert "Weather:" in response["answer"]


def test_at_risk_soon_with_real_predictor():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=7)
    predictor = TrendFailurePredictor(central_node_id=gen.central_node_id, window_size=10)
    last_snap = None
    for snap in gen.stream(ticks=8, anomaly_at=3, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1"):
        predictor.update(snap)
        last_snap = snap

    predictions = predict_failures(predictor)
    node_results = detect_anomalies(last_snap, central_node_id=gen.central_node_id)
    link_results = detect_link_anomalies(last_snap)

    response = ask_copilot(
        QueryIntent.AT_RISK_SOON, node_results, link_results, predictions, gen.topology, gen.central_node_id
    )
    assert isinstance(response["answer"], str)


def test_unknown_intent_raises():
    gen = SyntheticTelemetryGenerator(num_leaves=2, seed=8)
    try:
        ask_copilot("not_a_real_intent", [], [], [], gen.topology, gen.central_node_id)
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")