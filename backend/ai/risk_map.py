"""
backend/ai/risk_map.py

Feature 11/16 (global #41): Network Risk Map.

Reuses the same radial layout as Feature 6's graph_generation.py, but
colors/annotates nodes by PREDICTED risk (Feature 2's failure_probability)
instead of current severity -- "where is risk concentrated" rather than
"what's broken right now" (that's graph_generation.py's job). Same graph
shape (nodes/edges with x/y and color) so the dashboard can swap between
the two views without changing its rendering code.

SCOPE NOTE -- flagged, not silently expanded: only node-level risk is
mapped. Feature 2 (failure prediction) only produces per-node failure
probability, not link-level risk -- nothing predicts link congestion
trending yet. Links here show their CURRENT status (from Feature 1's link
detector), not a projection. Extending Feature 2 to links, or building a
link-specific predictor, is a bigger addition than this file should absorb
on its own -- worth a separate conversation if the dashboard needs it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from backend.ai.graph_generation import SEVERITY_COLOR
from backend.network.models import Topology


def _risk_severity(probability: float) -> str:
    if probability <= 0:
        return "none"
    if probability >= 0.85:
        return "critical"
    if probability >= 0.6:
        return "high"
    if probability >= 0.3:
        return "medium"
    return "low"


@dataclass
class RiskMapNode:
    id: str
    label: str
    x: float
    y: float
    is_central: bool
    failure_probability: float
    risk_severity: str
    color: str
    trend: str
    estimated_ticks_to_failure: Optional[int]

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class RiskMapEdge:
    id: str
    source: str
    target: str
    status: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class RiskMap:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    highest_risk_node: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "highest_risk_node": self.highest_risk_node,
        }


class RiskMapGenerator:
    def generate(
        self,
        topology: Topology,
        prediction_results: list,
        link_anomaly_results: list,
        central_node_id: str,
        radius: float = 300.0,
    ) -> RiskMap:
        pred_by_node = {p["node_id"]: p for p in prediction_results}
        leaves = [d.node_id for d in topology.devices if d.node_id != central_node_id]
        n = len(leaves)

        nodes = []
        for device in topology.devices:
            if device.node_id == central_node_id:
                x, y = 0.0, 0.0
            else:
                idx = leaves.index(device.node_id)
                angle = 2 * math.pi * idx / n if n else 0.0
                x, y = radius * math.cos(angle), radius * math.sin(angle)

            pred = pred_by_node.get(device.node_id)
            prob = pred["failure_probability"] if pred else 0.0
            trend = pred["trend"] if pred else "stable"
            eta = pred["estimated_ticks_to_failure"] if pred else None
            severity = _risk_severity(prob)

            nodes.append(
                RiskMapNode(
                    id=device.node_id,
                    label=device.node_id,
                    x=round(x, 1),
                    y=round(y, 1),
                    is_central=(device.node_id == central_node_id),
                    failure_probability=round(prob, 3),
                    risk_severity=severity,
                    color=SEVERITY_COLOR.get(severity, SEVERITY_COLOR["none"]),
                    trend=trend,
                    estimated_ticks_to_failure=eta,
                )
            )

        edges = []
        link_status = {r["link_id"]: r for r in link_anomaly_results}
        for link in topology.links:
            info = link_status.get(link.link_id, {"severity": "none"})
            edges.append(
                RiskMapEdge(
                    id=link.link_id,
                    source=link.source_id,
                    target=link.target_id,
                    status="down" if info["severity"] == "critical" else "up",
                )
            )

        highest = max(nodes, key=lambda n: n.failure_probability, default=None)
        highest_id = highest.id if highest and highest.failure_probability > 0 else None

        return RiskMap(nodes=nodes, edges=edges, highest_risk_node=highest_id)


def generate_risk_map(
    topology: Topology,
    prediction_results: list,
    link_anomaly_results: list,
    central_node_id: str,
    radius: float = 300.0,
    generator: Optional[RiskMapGenerator] = None,
) -> dict:
    generator = generator or RiskMapGenerator()
    return generator.generate(
        topology, prediction_results, link_anomaly_results, central_node_id, radius=radius
    ).to_dict()