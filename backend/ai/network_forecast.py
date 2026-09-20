"""
backend/ai/network_forecast.py

Feature 10/16 (global #40): Network Forecast / Network Weather.

No new detection -- aggregates Feature 2's per-node trend/slope predictions
into a network-wide short-term forecast: a projected resilience score at
some horizon N ticks out, plus an at-a-glance "weather" label, plus a list
of specific nodes expected to actually fail within that window (from
Feature 2's estimated_ticks_to_failure).

ASSUMPTION -- flagged: the score_delta formula below (momentum * scale *
horizon) is a hand-tuned heuristic, not fit to any real data -- there isn't
any yet. Recalibrate the SCALE constant once real incident history exists
to compare forecasts against what actually happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SCALE = 2.0  # heuristic points-per-tick at full momentum; see ASSUMPTION above


@dataclass
class NetworkForecast:
    horizon_ticks: int
    current_score: float
    forecast_score: float
    weather_condition: str  # "clear" | "cloudy" | "stormy" | "severe"
    worsening_count: int
    stable_count: int
    improving_count: int
    at_risk_within_horizon: list = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _weather_condition(score: float, momentum: float) -> str:
    if score >= 80 and momentum <= 0.1:
        return "clear"
    if score >= 60:
        return "cloudy"
    if score >= 30:
        return "stormy"
    return "severe"


def forecast_network_weather(
    prediction_results: list,
    current_resilience_score: float,
    horizon_ticks: int = 10,
) -> dict:
    """
    prediction_results: Feature 2's predict_failures() output.
    current_resilience_score: the resilience index's calculate_resilience_index()['score'].
    """
    worsening = [p for p in prediction_results if p["trend"] == "worsening"]
    improving = [p for p in prediction_results if p["trend"] == "improving"]
    stable = [p for p in prediction_results if p["trend"] == "stable"]
    total = len(prediction_results)

    momentum = (len(worsening) - len(improving)) / total if total else 0.0
    score_delta = -momentum * SCALE * horizon_ticks
    forecast_score = round(max(0.0, min(100.0, current_resilience_score + score_delta)), 1)

    at_risk = [
        p["node_id"]
        for p in prediction_results
        if p["estimated_ticks_to_failure"] is not None and p["estimated_ticks_to_failure"] <= horizon_ticks
    ]

    weather = _weather_condition(forecast_score, momentum)

    explanation = (
        f"{len(worsening)} worsening, {len(stable)} stable, {len(improving)} improving "
        f"over {total} tracked nodes. Projected score {current_resilience_score:.1f} -> "
        f"{forecast_score:.1f} over the next {horizon_ticks} ticks."
    )
    if at_risk:
        explanation += f" {len(at_risk)} node(s) predicted to fail within that window: {', '.join(at_risk)}."

    return NetworkForecast(
        horizon_ticks=horizon_ticks,
        current_score=round(current_resilience_score, 1),
        forecast_score=forecast_score,
        weather_condition=weather,
        worsening_count=len(worsening),
        stable_count=len(stable),
        improving_count=len(improving),
        at_risk_within_horizon=at_risk,
        explanation=explanation,
    ).to_dict()