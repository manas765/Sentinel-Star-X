"""
backend/ai/test_network_forecast.py
Run with: pytest backend/ai/test_network_forecast.py -v
"""

from backend.ai.network_forecast import forecast_network_weather


def _pred(node_id, trend, eta=None, prob=0.5):
    return {
        "node_id": node_id,
        "failure_probability": prob,
        "trend": trend,
        "estimated_ticks_to_failure": eta,
        "confidence": 0.8,
    }


def test_no_predictions_forecast_equals_current():
    forecast = forecast_network_weather([], current_resilience_score=90.0, horizon_ticks=10)
    assert forecast["forecast_score"] == 90.0
    assert forecast["worsening_count"] == 0
    assert forecast["at_risk_within_horizon"] == []


def test_all_stable_forecast_equals_current():
    preds = [_pred("leaf-0", "stable"), _pred("leaf-1", "stable")]
    forecast = forecast_network_weather(preds, current_resilience_score=85.0, horizon_ticks=10)
    assert forecast["forecast_score"] == 85.0
    assert forecast["weather_condition"] == "clear"


def test_all_worsening_lowers_forecast_below_current():
    preds = [_pred("leaf-0", "worsening"), _pred("leaf-1", "worsening")]
    forecast = forecast_network_weather(preds, current_resilience_score=90.0, horizon_ticks=10)
    assert forecast["forecast_score"] < 90.0
    assert forecast["weather_condition"] != "clear"


def test_all_improving_does_not_lower_forecast():
    preds = [_pred("leaf-0", "improving"), _pred("leaf-1", "improving")]
    forecast = forecast_network_weather(preds, current_resilience_score=70.0, horizon_ticks=10)
    assert forecast["forecast_score"] >= 70.0


def test_forecast_score_clamped_to_0_100():
    preds = [_pred(f"leaf-{i}", "worsening") for i in range(5)]
    forecast = forecast_network_weather(preds, current_resilience_score=5.0, horizon_ticks=50)
    assert 0.0 <= forecast["forecast_score"] <= 100.0

    preds_up = [_pred(f"leaf-{i}", "improving") for i in range(5)]
    forecast_up = forecast_network_weather(preds_up, current_resilience_score=98.0, horizon_ticks=50)
    assert 0.0 <= forecast_up["forecast_score"] <= 100.0


def test_at_risk_within_horizon_filters_correctly():
    preds = [
        _pred("leaf-0", "worsening", eta=3),
        _pred("leaf-1", "worsening", eta=15),
        _pred("leaf-2", "stable", eta=None),
    ]
    forecast = forecast_network_weather(preds, current_resilience_score=70.0, horizon_ticks=10)
    assert forecast["at_risk_within_horizon"] == ["leaf-0"]


def test_weather_condition_thresholds():
    assert forecast_network_weather([], 95.0, 5)["weather_condition"] == "clear"
    assert forecast_network_weather([], 65.0, 5)["weather_condition"] == "cloudy"
    assert forecast_network_weather([], 40.0, 5)["weather_condition"] == "stormy"
    assert forecast_network_weather([], 10.0, 5)["weather_condition"] == "severe"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")