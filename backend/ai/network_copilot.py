"""
backend/ai/network_copilot.py

Feature 13/16 (global #51): AI Network Copilot.

SCOPE FLAG -- flagged, not guessed: a real natural-language copilot needs
an LLM call (e.g. the Anthropic API) to parse arbitrary free text into
intent, and there's no API key/config info for this backend available
here, so that's not wired up silently. This is intent-based instead: a
small set of predefined query types, each of which aggregates several
other features into one answered question. Feature 14 (Natural-Language
What-If) is the natural place for actual free-text parsing once the team
picks an LLM provider/key setup -- that layer can translate free text into
calls to this module's intents rather than this module trying to do both.

Every intent reuses Features 1/2/4/6/8/12 -- no new detection logic here,
purely a query/answer layer over what they already compute.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.ai.explainable_ai import explain_network_state
from backend.ai.network_forecast import forecast_network_weather
from backend.ai.recovery_confidence import evaluate_recovery_confidence
from backend.ai.resilience_index import calculate_resilience_index
from backend.network.models import Topology


class QueryIntent(str, Enum):
    STATUS_SUMMARY = "status_summary"
    WHATS_WRONG = "whats_wrong"
    WHAT_TO_FIX_FIRST = "what_to_fix_first"
    RESILIENCE_SCORE = "resilience_score"
    FORECAST = "forecast"
    AT_RISK_SOON = "at_risk_soon"


@dataclass
class CopilotResponse:
    intent: str
    answer: str
    supporting_data: dict

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def ask_copilot(
    intent: QueryIntent,
    node_anomaly_results: list,
    link_anomaly_results: list,
    prediction_results: list,
    topology: Topology,
    central_node_id: str,
    horizon_ticks: int = 10,
) -> dict:
    if intent == QueryIntent.RESILIENCE_SCORE:
        report = calculate_resilience_index(
            node_anomaly_results, link_anomaly_results, prediction_results, topology, central_node_id
        )
        answer = f"Resilience index is {report['score']}/100. {report['explanation']}"
        return CopilotResponse(intent.value, answer, report).to_dict()

    if intent == QueryIntent.FORECAST:
        resilience = calculate_resilience_index(
            node_anomaly_results, link_anomaly_results, prediction_results, topology, central_node_id
        )
        forecast = forecast_network_weather(prediction_results, resilience["score"], horizon_ticks)
        answer = f"Weather: {forecast['weather_condition']}. {forecast['explanation']}"
        return CopilotResponse(intent.value, answer, forecast).to_dict()

    if intent == QueryIntent.AT_RISK_SOON:
        at_risk = [
            p
            for p in prediction_results
            if p["estimated_ticks_to_failure"] is not None and p["estimated_ticks_to_failure"] <= horizon_ticks
        ]
        if not at_risk:
            answer = f"Nothing predicted to fail within the next {horizon_ticks} ticks."
        else:
            names = ", ".join(f"{p['node_id']} (~{p['estimated_ticks_to_failure']} ticks)" for p in at_risk)
            answer = f"{len(at_risk)} node(s) at risk within {horizon_ticks} ticks: {names}."
        return CopilotResponse(intent.value, answer, {"at_risk": at_risk}).to_dict()

    if intent == QueryIntent.WHATS_WRONG:
        explanations = explain_network_state(node_anomaly_results, link_anomaly_results, topology, central_node_id)
        problems = [e for e in explanations if e["summary"] and "is healthy" not in e["summary"]]
        if not problems:
            answer = "Nothing's wrong right now -- everything's healthy."
        else:
            answer = " ".join(p["summary"] for p in problems)
        return CopilotResponse(intent.value, answer, {"problems": problems}).to_dict()

    if intent == QueryIntent.WHAT_TO_FIX_FIRST:
        confidence_results = evaluate_recovery_confidence(
            node_anomaly_results, link_anomaly_results, topology, central_node_id
        )
        actionable = [r for r in confidence_results if r["recommendation"] in ("act_here", "act_with_caution")]
        actionable.sort(key=lambda r: r["recovery_confidence"], reverse=True)
        if not actionable:
            answer = "Nothing needs fixing right now."
        else:
            top = actionable[0]
            answer = (
                f"Fix {top['target_id']} first -- {top['recommendation']} "
                f"(confidence {top['recovery_confidence']}). {top['explanation']}"
            )
        return CopilotResponse(intent.value, answer, {"priority_order": actionable}).to_dict()

    if intent == QueryIntent.STATUS_SUMMARY:
        resilience = calculate_resilience_index(
            node_anomaly_results, link_anomaly_results, prediction_results, topology, central_node_id
        )
        anomalous_count = sum(1 for r in node_anomaly_results + link_anomaly_results if r["is_anomalous"])
        if anomalous_count == 0:
            answer = f"Network is healthy. Resilience index: {resilience['score']}/100."
        else:
            answer = (
                f"Resilience index: {resilience['score']}/100. {anomalous_count} node(s)/link(s) "
                f"currently anomalous."
            )
        return CopilotResponse(intent.value, answer, resilience).to_dict()

    raise ValueError(f"Unknown intent: {intent}")