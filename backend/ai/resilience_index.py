"""
backend/ai/resilience_index.py

Feature 6/16 (global #36): SENTINEL Resilience Index.

Composite 0-100 score: node health (Feature 1), link health (Feature 1),
predicted failure risk (Feature 2), and a cascading-failure penalty
(Feature 4 -- one root cause taking down many nodes scores worse than the
same total severity spread across independent, unrelated issues).

ASSUMPTION -- flagged: star topology has zero path redundancy by
construction (every leaf has exactly one link to the central switch), so
this doesn't add a separate "redundancy" term -- Akshata's Critical Path
Protection already covers that on the topology side. If she exposes a
redundancy score via her API, it probably belongs as an input here rather
than reimplemented -- worth checking rather than guessing at her data shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.ai.root_cause_analysis import analyze_root_causes
from backend.network.models import Topology

SEVERITY_WEIGHT = {"none": 0.0, "low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}


@dataclass
class ResilienceReport:
    score: float  # 0-100, higher is healthier
    node_health: float  # 0-1
    link_health: float  # 0-1
    prediction_risk: float  # 0-1, higher = riskier
    cascade_penalty: float  # 0-1, fraction of network caught in one cascading incident
    explanation: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class ResilienceIndexCalculator:
    def calculate(
        self,
        node_anomaly_results: list,
        link_anomaly_results: list,
        prediction_results: list,
        topology: Topology,
        central_node_id: str,
    ) -> ResilienceReport:
        node_health = self._avg_health(node_anomaly_results)
        link_health = self._avg_health(link_anomaly_results)

        avg_risk = (
            sum(p["failure_probability"] for p in prediction_results) / len(prediction_results)
            if prediction_results
            else 0.0
        )

        rca_results = analyze_root_causes(
            node_anomaly_results, link_anomaly_results, topology, central_node_id
        )
        total_targets = len(node_anomaly_results) + len(link_anomaly_results)
        cascade_penalty = 0.0
        if rca_results and total_targets:
            biggest_cluster = max(
                len(c["affected_nodes"]) + len(c["affected_links"]) + 1 for c in rca_results
            )
            cascade_penalty = min(biggest_cluster / total_targets, 1.0)

        score = 100 * (
            0.35 * node_health
            + 0.15 * link_health
            + 0.25 * (1 - avg_risk)
            + 0.25 * (1 - cascade_penalty)
        )

        explanation = (
            f"node_health={node_health:.2f}, link_health={link_health:.2f}, "
            f"prediction_risk={avg_risk:.2f}, cascade_penalty={cascade_penalty:.2f}"
        )

        return ResilienceReport(
            score=round(max(0.0, min(100.0, score)), 1),
            node_health=round(node_health, 3),
            link_health=round(link_health, 3),
            prediction_risk=round(avg_risk, 3),
            cascade_penalty=round(cascade_penalty, 3),
            explanation=explanation,
        )

    @staticmethod
    def _avg_health(results: list) -> float:
        if not results:
            return 1.0
        total = sum(1 - SEVERITY_WEIGHT.get(r["severity"], 0.0) for r in results)
        return total / len(results)


def calculate_resilience_index(
    node_anomaly_results: list,
    link_anomaly_results: list,
    prediction_results: list,
    topology: Topology,
    central_node_id: str,
    calculator: Optional[ResilienceIndexCalculator] = None,
) -> dict:
    calculator = calculator or ResilienceIndexCalculator()
    return calculator.calculate(
        node_anomaly_results, link_anomaly_results, prediction_results, topology, central_node_id
    ).to_dict()