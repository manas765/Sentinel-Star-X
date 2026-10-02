"""
backend/ai/whatif_engine.py

Feature 14/16 (global #52): Natural-Language What-If.

SCOPE FLAG #1 -- same as Feature 13: real free-text parsing needs an LLM
call, and there's no API key/config confirmed for this backend. Structured
params (scenario type + target id) instead of actual natural language,
same shape as the Copilot's intents. If/when the team wires up an LLM,
that layer translates free text into calls to simulate_what_if() below.

SCOPE FLAG #2 -- real overlap, not guessed away: Akshata already built a
Digital Twin Sandbox / What-If Lab ("forks the twin, runs scenarios, never
touches the real network"). This file uses OUR OWN synthetic generator to
inject the hypothetical anomaly, not her actual twin/sandbox -- so this
answers "what would the AI's analysis layer conclude" given a hypothetical,
not "what would actually happen to the real network" (that's her sandbox's
job, and it's the more authoritative answer). Same shape as the Incident
Replay / Network Memory split flagged earlier: worth checking whether this
should consume her sandbox's forked state instead of a fresh synthetic
snapshot, once her sandbox API is available to read.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.explainable_ai import explain_network_state
from backend.ai.recovery_confidence import evaluate_recovery_confidence
from backend.ai.resilience_index import calculate_resilience_index
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


@dataclass
class WhatIfResult:
    scenario: str
    target: str
    baseline_score: float
    projected_score: float
    score_delta: float
    affected_nodes: list
    affected_links: list
    explanations: list
    recommendation: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def simulate_what_if(generator: SyntheticTelemetryGenerator, scenario: str, target: str) -> dict:
    """
    Runs a hypothetical anomaly through the full analysis pipeline using a
    fresh synthetic snapshot (see SCOPE FLAG #2) and compares against a
    clean baseline snapshot from the same generator/topology.

    scenario: an AnomalyType value, e.g. "node_down", "link_congestion".
    target: a node_id or link_id from generator.topology.
    """
    try:
        anomaly_type = AnomalyType(scenario)
    except ValueError:
        raise ValueError(f"Unknown scenario: {scenario}. Valid: {[a.value for a in AnomalyType]}")

    baseline_snapshot = generator.generate_snapshot()
    baseline_nodes = detect_anomalies(baseline_snapshot, central_node_id=generator.central_node_id)
    baseline_links = detect_link_anomalies(baseline_snapshot)
    baseline_report = calculate_resilience_index(
        baseline_nodes, baseline_links, [], generator.topology, generator.central_node_id
    )

    what_if_snapshot = generator.generate_snapshot(anomaly=anomaly_type, anomaly_target=target)
    wi_nodes = detect_anomalies(what_if_snapshot, central_node_id=generator.central_node_id)
    wi_links = detect_link_anomalies(what_if_snapshot)
    wi_report = calculate_resilience_index(wi_nodes, wi_links, [], generator.topology, generator.central_node_id)

    rca = analyze_root_causes(wi_nodes, wi_links, generator.topology, generator.central_node_id)
    affected_nodes = sorted(
        {n for c in rca for n in c["affected_nodes"]}
        | {c["root_cause_id"] for c in rca if c["root_cause_type"] == "node"}
    )
    affected_links = sorted(
        {l for c in rca for l in c["affected_links"]}
        | {c["root_cause_id"] for c in rca if c["root_cause_type"] == "link"}
    )

    explanations = explain_network_state(wi_nodes, wi_links, generator.topology, generator.central_node_id)
    explanations = [e for e in explanations if e["summary"] and "is healthy" not in e["summary"]]

    confidence_results = evaluate_recovery_confidence(
        wi_nodes, wi_links, generator.topology, generator.central_node_id
    )
    actionable = [r for r in confidence_results if r["recommendation"] in ("act_here", "act_with_caution")]
    if actionable:
        top = max(actionable, key=lambda r: r["recovery_confidence"])
        recommendation = f"If this happens: {top['target_id']} would need attention ({top['recommendation']})."
    else:
        recommendation = "No clear recovery action identified for this scenario."

    return WhatIfResult(
        scenario=scenario,
        target=target,
        baseline_score=baseline_report["score"],
        projected_score=wi_report["score"],
        score_delta=round(wi_report["score"] - baseline_report["score"], 1),
        affected_nodes=affected_nodes,
        affected_links=affected_links,
        explanations=explanations,
        recommendation=recommendation,
    ).to_dict()