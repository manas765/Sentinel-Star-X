from typing import Dict, List

import networkx as nx

from .attack_path_models import AttackPath

# How much each additional hop reduces a path's risk — attacks are harder
# to carry further, so risk decays with distance from the compromised node.
HOP_DECAY_FACTOR = 0.8
MAX_HOPS = 4


class AttackPathAnalyzer:
    """
    Given a network topology graph and the current threat level of each node,
    finds and ranks the paths a threat could realistically spread along from
    a compromised node. This uses a standalone networkx graph for now — it
    can be pointed at the real topology from the Network module once built.
    """

    def __init__(self, graph: nx.Graph) -> None:
        self.graph = graph

    def find_attack_paths(
        self, source_node: str, node_threat_scores: Dict[str, float]
    ) -> List[AttackPath]:
        """
        node_threat_scores: entity_id -> risk score (0.0-1.0), e.g. from
        SecurityAnomalyDetector (#13) or ThreatLevelManager (#15).
        Nodes not present are assumed NORMAL (risk 0.0).
        """
        if source_node not in self.graph:
            return []

        paths: List[AttackPath] = []
        for target_node in self.graph.nodes:
            if target_node == source_node:
                continue
            try:
                shortest = nx.shortest_path(self.graph, source_node, target_node)
            except nx.NetworkXNoPath:
                continue

            if len(shortest) - 1 > MAX_HOPS:
                continue

            risk = self._score_path(shortest, node_threat_scores)
            paths.append(AttackPath(nodes=shortest, risk_score=risk))

        paths.sort(key=lambda p: p.risk_score, reverse=True)
        return paths

    def _score_path(self, nodes: List[str], node_threat_scores: Dict[str, float]) -> float:
        hops = len(nodes) - 1
        distance_factor = HOP_DECAY_FACTOR ** hops

        # A path is riskier if it passes through nodes that are already
        # under elevated threat — an attacker could pivot through them.
        intermediate_nodes = nodes[1:-1]
        if intermediate_nodes:
            avg_intermediate_risk = sum(
                node_threat_scores.get(n, 0.0) for n in intermediate_nodes
            ) / len(intermediate_nodes)
        else:
            avg_intermediate_risk = 0.0

        target_risk_relevance = node_threat_scores.get(nodes[-1], 0.0)

        base_risk = 0.5 + 0.3 * avg_intermediate_risk + 0.2 * target_risk_relevance
        return round(min(1.0, base_risk * distance_factor), 4)

    def highest_risk_targets(
        self, source_node: str, node_threat_scores: Dict[str, float], top_n: int = 3
    ) -> List[AttackPath]:
        return self.find_attack_paths(source_node, node_threat_scores)[:top_n]