"""
backend/network/cascade_predictor.py

Cascading Failure Prediction (feature 6.17).

This is a RULE-BASED heuristic baseline, not a trained model - it exists so
Network + Digital Twin has *something* producing cascade probability out
of the box. The AI/Prediction track (feature 6.7, Predictive Failure
Detection) owns the ML model; when that exists, swap the
`_estimate_stress_probability` heuristic below for their model's output
rather than duplicating a second model here.

Chain this heuristic follows (from the doc):
    switch overload -> latency increase -> packet loss -> retransmission
    -> traffic increase -> congestion -> additional failures

Approach: a node is "stressed" if its telemetry shows elevated latency,
packet loss, or utilization. Stress on a highly-connected node (the
central switch) is weighted far higher, since in a Star topology losing
the switch cascades to every leaf - that's the whole point of a Star's
single point of failure.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.network.service_graph import ServiceDependencyGraph

_LATENCY_STRESS_MS = 40.0
_PACKET_LOSS_STRESS_PCT = 3.0
_CPU_STRESS_PCT = 75.0


@dataclass
class CascadePrediction:
    source_node: str
    cascade_probability: float       # 0.0-1.0
    likely_affected_nodes: list
    likely_affected_services: list
    preventive_recommendation: str


def _node_stress_score(node: dict) -> float:
    """0.0 (no stress) to 1.0 (very stressed), based on early-warning
    signals rather than the node already being down."""
    if node["status"] == "down":
        return 1.0
    signals = [
        min(1.0, node["latency_ms"] / _LATENCY_STRESS_MS),
        min(1.0, node["packet_loss_pct"] / _PACKET_LOSS_STRESS_PCT),
        min(1.0, node["cpu_util_pct"] / _CPU_STRESS_PCT),
    ]
    return sum(signals) / len(signals)


class CascadePredictor:
    def __init__(self):
        self._service_graph = ServiceDependencyGraph()

    def predict(self, twin_state: dict) -> list:
        """Returns a CascadePrediction per node currently showing enough
        stress to be worth flagging (score > 0.3), sorted worst-first."""
        nodes_by_id = {n["node_id"]: n for n in twin_state["nodes"]}
        neighbors = self._build_adjacency(twin_state["links"])
        service_status = self._service_graph.compute_status(twin_state)

        predictions = []
        for node in twin_state["nodes"]:
            stress = _node_stress_score(node)
            if stress <= 0.3:
                continue

            is_central = node["is_central"]
            # A stressed central switch threatens every leaf attached to it;
            # a stressed leaf only threatens itself and its direct neighbors.
            fanout_multiplier = 1.0 if is_central else 0.4
            cascade_probability = round(min(1.0, stress * fanout_multiplier * 1.2), 3)

            affected_nodes = neighbors.get(node["node_id"], [])
            if is_central:
                affected_nodes = list(nodes_by_id.keys())  # everyone downstream of the switch

            affected_services = [
                s for s, result in service_status.items()
                if result.status != "up" or node["node_id"] in result.providing_nodes
            ]

            if is_central:
                recommendation = (
                    f"Central switch under stress (score {stress:.2f}). "
                    "Reduce traffic multiplier, consider promoting backup switch, "
                    "or shed non-critical leaf traffic before latency cascades network-wide."
                )
            else:
                recommendation = (
                    f"{node['node_id']} under stress (score {stress:.2f}). "
                    f"Consider throttling its traffic or isolating it before its "
                    f"link congestion spreads to neighbors: {affected_nodes}."
                )

            predictions.append(CascadePrediction(
                source_node=node["node_id"],
                cascade_probability=cascade_probability,
                likely_affected_nodes=affected_nodes,
                likely_affected_services=affected_services,
                preventive_recommendation=recommendation,
            ))

        return sorted(predictions, key=lambda p: p.cascade_probability, reverse=True)

    @staticmethod
    def _build_adjacency(links: list) -> dict:
        adjacency: dict[str, list] = {}
        for link in links:
            # link_id is "source<->target" per network/models.py
            source, target = link["link_id"].split("<->")
            adjacency.setdefault(source, []).append(target)
            adjacency.setdefault(target, []).append(source)
        return adjacency
