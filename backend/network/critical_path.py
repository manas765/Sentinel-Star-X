"""
backend/network/critical_path.py

Critical Path Protection (feature 6.20).

Identifies which physical paths carry traffic for critical services, and -
during a hypothetical failure - checks whether an alternate path exists in
the current topology. In a pure Star (every leaf has exactly one link to
the central switch), there IS no alternate path once that one link or the
switch itself fails; this module says so honestly rather than inventing
one. An alternate only exists once a backup link/switch has actually been
created (via NetworkSimulator.create_link / a backup switch), which is
exactly the kind of change Dynamic Topology Morphing (6.24) and the
Topology Recommendation Engine (6.61) are for.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from backend.network.service_graph import ServiceDependencyGraph

# A node counts as "critical" if it's the sole/majority provider of one of
# these services. Kept in sync with service_graph's own critical-ish set.
_CRITICAL_SERVICES = {"authentication", "database", "network"}


@dataclass
class CriticalPath:
    node_id: str
    service: str
    path: list              # sequence of node_ids from node to central switch
    has_redundant_path: bool
    alternate_path: list | None
    protection_note: str


class CriticalPathProtector:
    def __init__(self):
        self.service_graph = ServiceDependencyGraph()

    def _build_graph(self, twin_state: dict) -> nx.Graph:
        g = nx.Graph()
        for node in twin_state["nodes"]:
            g.add_node(node["node_id"])
        for link in twin_state["links"]:
            if link["status"] == "down":
                continue
            source, target = link["link_id"].split("<->")
            g.add_edge(source, target)
        return g

    def get_critical_paths(self, twin_state: dict) -> list:
        """One CriticalPath entry per (critical service, providing node)."""
        graph = self._build_graph(twin_state)
        central_id = next(n["node_id"] for n in twin_state["nodes"] if n["is_central"])
        service_statuses = self.service_graph.compute_status(twin_state)

        results = []
        for service_name in _CRITICAL_SERVICES:
            status = service_statuses.get(service_name)
            if not status:
                continue
            for node_id in status.providing_nodes:
                if node_id == central_id:
                    continue
                try:
                    path = nx.shortest_path(graph, node_id, central_id)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    path = []

                # Redundant iff removing the first edge on the path still
                # leaves a path - i.e. there's more than one edge-disjoint
                # route to the switch.
                has_redundant = False
                alternate = None
                if len(path) >= 2:
                    trimmed = graph.copy()
                    trimmed.remove_edge(path[0], path[1])
                    try:
                        alternate = nx.shortest_path(trimmed, node_id, central_id)
                        has_redundant = True
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        has_redundant = False

                note = (
                    f"Redundant path available via {alternate}."
                    if has_redundant
                    else "No redundant path exists in current topology - a link/switch "
                         "failure here would isolate this node. Needs a backup link or "
                         "topology change (6.24/6.61) to protect."
                )

                results.append(CriticalPath(
                    node_id=node_id,
                    service=service_name,
                    path=path,
                    has_redundant_path=has_redundant,
                    alternate_path=alternate,
                    protection_note=note,
                ))

        return results
