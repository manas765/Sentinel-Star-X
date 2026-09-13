"""
backend/network/service_graph.py

Service Dependency Graph (feature 6.19).

The doc's example chain is:
    Users -> Authentication -> Application Server -> Database

The point (per the doc): "the system should understand service impact
rather than only device status." A single dead PC matters much less than
the one server backing Authentication for everyone downstream.

This maps DeviceType -> which service(s) that device provides, builds the
dependency chain as a directed graph (uses networkx, already a project
dependency), and computes each service's status by combining:
  (a) the status of the node(s) providing that service, and
  (b) whether anything it DEPENDS ON is already degraded/down.

Critical Service Protection (6.18) and Critical Path Protection (6.20)
consume this graph's output rather than duplicating the mapping.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from backend.network.models import DeviceType

# Which service each device type provides. A device can back more than one
# service's nodes but here each device_type maps to exactly one, matching
# how the simulator currently assigns device types.
_DEVICE_TO_SERVICE = {
    DeviceType.SERVER_AUTH: "authentication",
    DeviceType.SERVER_DB: "database",
    DeviceType.SERVER_MONITORING: "monitoring",
    DeviceType.CENTRAL_SWITCH: "network",
    DeviceType.BACKUP_SWITCH: "network",
}
# Anything else (PC, IOT, GUEST, BACKUP, CRITICAL) is a client of "application",
# not a provider of it - "application" is provided by the network fabric itself
# reaching those clients, so it depends on "network" only.
_DEFAULT_SERVICE = "application"

_STATUS_SCORE = {"up": 1.0, "degraded": 0.5, "down": 0.0}


@dataclass
class ServiceStatus:
    service: str
    status: str          # "up" | "degraded" | "down"
    score: float          # 0.0-1.0
    providing_nodes: list
    reason: str


class ServiceDependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        # edges point FROM the dependent service TO what it depends on
        self.graph.add_edge("users", "authentication")
        self.graph.add_edge("authentication", "application")
        self.graph.add_edge("application", "database")
        self.graph.add_edge("application", "network")
        self.graph.add_edge("authentication", "network")
        self.graph.add_edge("database", "network")
        self.graph.add_edge("monitoring", "network")

    def services(self) -> list:
        return list(self.graph.nodes)

    def dependencies_of(self, service: str) -> list:
        """What `service` needs to be healthy in order to itself be healthy."""
        return list(self.graph.successors(service))

    def dependents_of(self, service: str) -> list:
        """What breaks if `service` breaks."""
        return list(self.graph.predecessors(service))

    def _providing_nodes(self, service: str, twin_state: dict) -> list:
        result = []
        for node in twin_state["nodes"]:
            dtype = DeviceType(node["device_type"])
            provided = _DEVICE_TO_SERVICE.get(dtype, _DEFAULT_SERVICE)
            if provided == service:
                result.append(node)
        return result

    def compute_status(self, twin_state: dict) -> dict:
        """
        twin_state: the dict from DigitalTwin.get_state().
        Returns {service_name: ServiceStatus}, computed bottom-up so a
        service's dependencies are resolved before the service itself
        (i.e. database/network before application before authentication
        before users) - that's what makes this "impact" rather than just
        per-node status.
        """
        results: dict[str, ServiceStatus] = {}

        # "users" has no providing nodes of its own - it's a stand-in for
        # "everyone using the network," so it just inherits from what it
        # depends on. Process everything else in dependency order first.
        order = [s for s in nx.topological_sort(self.graph) if s != "users"]
        order.append("users")

        for service in order:
            providing_nodes = self._providing_nodes(service, twin_state)
            deps = self.dependencies_of(service)
            dep_scores = [results[d].score for d in deps if d in results]

            if providing_nodes:
                own_score = sum(_STATUS_SCORE.get(n["status"], 0.0) for n in providing_nodes) / len(providing_nodes)
            else:
                own_score = 1.0  # no nodes of its own (e.g. "users") - fully depends on dep_scores

            combined_score = own_score * (min(dep_scores) if dep_scores else 1.0)

            if combined_score >= 0.9:
                status = "up"
                reason = "all providing nodes and dependencies healthy"
            elif combined_score > 0.0:
                status = "degraded"
                blockers = [n["node_id"] for n in providing_nodes if n["status"] != "up"]
                weak_deps = [d for d in deps if results.get(d) and results[d].status != "up"]
                reason = f"degraded nodes: {blockers or 'none'}; degraded dependencies: {weak_deps or 'none'}"
            else:
                status = "down"
                reason = "no healthy providing nodes or a hard dependency is fully down"

            results[service] = ServiceStatus(
                service=service,
                status=status,
                score=round(combined_score, 3),
                providing_nodes=[n["node_id"] for n in providing_nodes],
                reason=reason,
            )

        return results
