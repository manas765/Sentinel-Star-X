"""
backend/ai/graph_generation.py

Feature 6/16 (global #35): Automatic Graph Generation.

Generates a ready-to-render graph structure (nodes + edges, with layout
positions and severity-based color coding baked in) combining topology
with live health/anomaly state from Features 1 and 3, so the dashboard
doesn't need to compute layout or color-mapping itself.

ASSUMPTION -- flagged: layout is a simple radial/star layout (central node
at origin, leaves evenly spaced in a circle) since that's trivially correct
for a star topology and needs no layout library. If Aakash's Command Center
Dashboard does its own layout, the x/y here are redundant and only the
styling (colors/status/labels) matters -- worth checking with him rather
than assuming he needs positions at all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.network.models import Topology

SEVERITY_COLOR = {
    "none": "#2ecc71",
    "low": "#f1c40f",
    "medium": "#e67e22",
    "high": "#e74c3c",
    "critical": "#8e0000",
}


@dataclass
class GraphNode:
    id: str
    label: str
    x: float
    y: float
    is_central: bool
    status: str
    severity: str
    color: str
    category: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    status: str
    severity: str
    color: str
    category: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class NetworkGraph:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"nodes": [n.to_dict() for n in self.nodes], "edges": [e.to_dict() for e in self.edges]}


class GraphGenerator:
    """v1: radial star layout + severity-based color coding, built from
    Feature 1 (anomaly detection) + Feature 3 (classification) output."""

    def generate(
        self,
        topology: Topology,
        node_anomaly_results: list,
        link_anomaly_results: list,
        central_node_id: str,
        radius: float = 300.0,
    ) -> NetworkGraph:
        node_class = {c["node_id"]: c for c in classify_failures(node_anomaly_results)}
        link_class = {c["link_id"]: c for c in classify_link_failures(link_anomaly_results)}
        node_anom = {r["node_id"]: r for r in node_anomaly_results}

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

            info = node_anom.get(device.node_id, {"severity": "none"})
            cls = node_class.get(device.node_id, {"category": "none"})
            nodes.append(
                GraphNode(
                    id=device.node_id,
                    label=device.node_id,
                    x=round(x, 1),
                    y=round(y, 1),
                    is_central=(device.node_id == central_node_id),
                    status="down" if cls["category"] == "node_down" else "up",
                    severity=info["severity"],
                    color=SEVERITY_COLOR.get(info["severity"], SEVERITY_COLOR["none"]),
                    category=cls["category"],
                )
            )

        edges = []
        for link in topology.links:
            info = next(
                (r for r in link_anomaly_results if r["link_id"] == link.link_id), {"severity": "none"}
            )
            cls = link_class.get(link.link_id, {"category": "none"})
            edges.append(
                GraphEdge(
                    id=link.link_id,
                    source=link.source_id,
                    target=link.target_id,
                    status="down" if cls["category"] == "link_down" else "up",
                    severity=info["severity"],
                    color=SEVERITY_COLOR.get(info["severity"], SEVERITY_COLOR["none"]),
                    category=cls["category"],
                )
            )

        return NetworkGraph(nodes=nodes, edges=edges)


def generate_graph(
    topology: Topology,
    node_anomaly_results: list,
    link_anomaly_results: list,
    central_node_id: str,
    radius: float = 300.0,
    generator: Optional[GraphGenerator] = None,
) -> dict:
    generator = generator or GraphGenerator()
    return generator.generate(
        topology, node_anomaly_results, link_anomaly_results, central_node_id, radius=radius
    ).to_dict()