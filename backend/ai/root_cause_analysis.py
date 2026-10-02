"""
backend/ai/root_cause_analysis.py

Feature 4/16 (global #9): Root Cause Analysis.

Approach: rule-based correlation over Feature 1's node + link anomaly
results, using topology adjacency (star: every leaf has exactly one link
to the central switch) to separate root causes from downstream symptoms.
Example: central switch degrades -> every leaf shows latency/packet_loss
symptoms simultaneously. Naive classification would flag N separate
problems; this groups them into one root cause + N symptoms.

INTERFACE FLAG -- not guessed past this point:
Akshata's track already has a Service Dependency Graph and Network
Dependency Analysis (live under /api/network/*) that likely give richer
downstream-impact chains than the direct star-adjacency used here (e.g.
service-level cascades: node -> service -> other services). This file only
uses the topology object's direct links, since that's what's available
locally. Worth checking with her whether RCA should call her dependency
endpoints instead of/in addition to this -- flagging rather than
reimplementing her topology logic by guesswork.

Also inherits the same failure-vs-security caveat as failure_classification.py:
a root cause tagged possible_security should be treated as provisional
until Manas's differentiator weighs in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.ai.failure_classification import (
    FailureCategory,
    classify_failures,
    classify_link_failures,
)
from backend.network.models import Topology


@dataclass
class RootCauseResult:
    cluster_id: int
    root_cause_type: str        # "node" | "link"
    root_cause_id: str
    root_cause_category: str    # FailureCategory value
    affected_nodes: list = field(default_factory=list)
    affected_links: list = field(default_factory=list)
    confidence: float = 0.0
    possible_security: bool = False
    explanation: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class RootCauseAnalyzer:
    """v1: rule-based, using star-topology adjacency (central <-> each leaf,
    one link each) to group correlated anomalies into root cause + symptoms."""

    def analyze(
        self,
        node_anomaly_results: list,
        link_anomaly_results: list,
        topology: Topology,
        central_node_id: str,
    ) -> list:
        node_classified = {c["node_id"]: c for c in classify_failures(node_anomaly_results)}
        link_classified = {c["link_id"]: c for c in classify_link_failures(link_anomaly_results)}

        anomalous_nodes = {
            nid: c for nid, c in node_classified.items() if c["category"] != FailureCategory.NONE.value
        }
        anomalous_links = {
            lid: c for lid, c in link_classified.items() if c["category"] != FailureCategory.NONE.value
        }

        link_by_leaf = self._link_by_leaf(topology, central_node_id)

        clusters = []
        cluster_id = 0
        explained_nodes = set()
        explained_links = set()

        # Rule 1: central node anomalous -> root cause for every other
        # anomalous leaf, since in a star topology everything routes through it.
        if central_node_id in anomalous_nodes:
            central_info = anomalous_nodes[central_node_id]
            affected = [nid for nid in anomalous_nodes if nid != central_node_id]
            affected_links = list(anomalous_links.keys())
            clusters.append(
                RootCauseResult(
                    cluster_id=cluster_id,
                    root_cause_type="node",
                    root_cause_id=central_node_id,
                    root_cause_category=central_info["category"],
                    affected_nodes=affected,
                    affected_links=affected_links,
                    confidence=central_info["confidence"],
                    possible_security=central_info["possible_security"],
                    explanation=(
                        f"Central switch is {central_info['category']}; every other "
                        f"anomalous node/link routes through it, so they're treated "
                        f"as downstream symptoms rather than independent problems."
                    ),
                )
            )
            cluster_id += 1
            explained_nodes.add(central_node_id)
            explained_nodes.update(affected)
            explained_links.update(affected_links)

        # Rule 2: link anomalous + its leaf also anomalous with
        # network-path-shaped symptoms (not its own resource usage) ->
        # link is the root cause, leaf's anomaly is a symptom.
        for link_id, link_info in anomalous_links.items():
            if link_id in explained_links:
                continue
            leaf_id = link_by_leaf.get(link_id)
            if leaf_id and leaf_id in anomalous_nodes and leaf_id not in explained_nodes:
                leaf_reasons = anomalous_nodes[leaf_id]["contributing_reasons"]
                resource_based = any(
                    r.startswith("cpu_util_pct") or r.startswith("mem_util_pct") for r in leaf_reasons
                )
                if not resource_based:
                    clusters.append(
                        RootCauseResult(
                            cluster_id=cluster_id,
                            root_cause_type="link",
                            root_cause_id=link_id,
                            root_cause_category=link_info["category"],
                            affected_nodes=[leaf_id],
                            affected_links=[],
                            confidence=link_info["confidence"],
                            possible_security=link_info["possible_security"],
                            explanation=(
                                f"Link {link_id} is {link_info['category']}; {leaf_id}'s "
                                f"symptoms are network-path-shaped (not cpu/mem), so the "
                                f"link is treated as the root cause, not the node itself."
                            ),
                        )
                    )
                    cluster_id += 1
                    explained_links.add(link_id)
                    explained_nodes.add(leaf_id)

        # Rule 3: anything left over is its own root cause -- no upstream
        # explanation found among what was checked.
        for node_id, info in anomalous_nodes.items():
            if node_id in explained_nodes:
                continue
            clusters.append(
                RootCauseResult(
                    cluster_id=cluster_id,
                    root_cause_type="node",
                    root_cause_id=node_id,
                    root_cause_category=info["category"],
                    confidence=info["confidence"],
                    possible_security=info["possible_security"],
                    explanation=f"{node_id} is {info['category']} with no correlated upstream cause found.",
                )
            )
            cluster_id += 1

        for link_id, info in anomalous_links.items():
            if link_id in explained_links:
                continue
            clusters.append(
                RootCauseResult(
                    cluster_id=cluster_id,
                    root_cause_type="link",
                    root_cause_id=link_id,
                    root_cause_category=info["category"],
                    confidence=info["confidence"],
                    possible_security=info["possible_security"],
                    explanation=f"{link_id} is {info['category']} with no correlated upstream cause found.",
                )
            )
            cluster_id += 1

        return clusters

    @staticmethod
    def _link_by_leaf(topology: Topology, central_node_id: str) -> dict:
        """link_id -> leaf_node_id, for direct central<->leaf links only."""
        mapping = {}
        for link in topology.links:
            if link.source_id == central_node_id:
                mapping[link.link_id] = link.target_id
            elif link.target_id == central_node_id:
                mapping[link.link_id] = link.source_id
        return mapping


def analyze_root_causes(
    node_anomaly_results: list,
    link_anomaly_results: list,
    topology: Topology,
    central_node_id: str,
    analyzer: Optional[RootCauseAnalyzer] = None,
) -> list:
    """Convenience entry point. Returns JSON-able list[dict]."""
    analyzer = analyzer or RootCauseAnalyzer()
    return [
        c.to_dict()
        for c in analyzer.analyze(node_anomaly_results, link_anomaly_results, topology, central_node_id)
    ]