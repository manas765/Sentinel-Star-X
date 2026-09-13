"""
backend/network/dependency_analyzer.py

Network Dependency Analysis (feature 6.49).

Calculates downstream impact of a node, link, or service failure. Rather
than re-deriving impact rules from scratch, this leans on two things you
already have: WhatIfSandbox (to safely simulate the failure on a forked
copy - never the real network) and ServiceDependencyGraph (to translate
device-level impact into service-level impact).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.digital_twin.sandbox import WhatIfSandbox
from backend.digital_twin.twin import DigitalTwin
from backend.network.service_graph import ServiceDependencyGraph


@dataclass
class DependencyImpact:
    failure_type: str      # "node" | "link" | "service"
    failure_target: str
    nodes_affected: list
    links_affected: list
    services_before: dict  # service -> status
    services_after: dict
    newly_degraded_services: list
    newly_down_services: list


class DependencyAnalyzer:
    def __init__(self, real_twin: DigitalTwin):
        self.real_twin = real_twin
        self.sandbox = WhatIfSandbox(real_twin)
        self.service_graph = ServiceDependencyGraph()

    def _service_diff(self, before: dict, after: dict) -> tuple:
        newly_degraded, newly_down = [], []
        for name, after_status in after.items():
            before_status = before.get(name)
            if before_status is None:
                continue
            if before_status.status == "up" and after_status.status == "degraded":
                newly_degraded.append(name)
            elif before_status.status != "down" and after_status.status == "down":
                newly_down.append(name)
        return newly_degraded, newly_down

    def analyze_node_failure(self, node_id: str) -> DependencyImpact:
        before_state = self.real_twin.get_state()
        before_services = self.service_graph.compute_status(before_state)

        result = self.sandbox.run_scenario(
            f"analyze-node-{node_id}", lambda sim: sim.fail_node(node_id), ticks=2,
        )
        after_services = self.service_graph.compute_status(result.final_state)
        newly_degraded, newly_down = self._service_diff(before_services, after_services)

        return DependencyImpact(
            failure_type="node",
            failure_target=node_id,
            nodes_affected=result.nodes_down,
            links_affected=result.links_down,
            services_before={k: v.status for k, v in before_services.items()},
            services_after={k: v.status for k, v in after_services.items()},
            newly_degraded_services=newly_degraded,
            newly_down_services=newly_down,
        )

    def analyze_link_failure(self, link_id: str) -> DependencyImpact:
        before_state = self.real_twin.get_state()
        before_services = self.service_graph.compute_status(before_state)

        result = self.sandbox.run_scenario(
            f"analyze-link-{link_id}", lambda sim: sim.fail_link(link_id), ticks=2,
        )
        after_services = self.service_graph.compute_status(result.final_state)
        newly_degraded, newly_down = self._service_diff(before_services, after_services)

        return DependencyImpact(
            failure_type="link",
            failure_target=link_id,
            nodes_affected=result.nodes_down,
            links_affected=result.links_down,
            services_before={k: v.status for k, v in before_services.items()},
            services_after={k: v.status for k, v in after_services.items()},
            newly_degraded_services=newly_degraded,
            newly_down_services=newly_down,
        )

    def analyze_service_failure(self, service_name: str) -> DependencyImpact:
        """No sandbox mutation needed here - a service failing IS a graph
        query (who depends on it), not a physical event to simulate."""
        state = self.real_twin.get_state()
        before_services = self.service_graph.compute_status(state)
        dependents = self.service_graph.dependents_of(service_name)

        # "after" is hypothetical: assume this service is fully down and
        # walk dependents to see what else would go down as a result.
        hypothetical_down = {service_name}
        changed = True
        while changed:
            changed = False
            for name in self.service_graph.services():
                if name in hypothetical_down:
                    continue
                deps = self.service_graph.dependencies_of(name)
                if any(d in hypothetical_down for d in deps):
                    hypothetical_down.add(name)
                    changed = True

        after_services = {
            name: ("down" if name in hypothetical_down else before_services[name].status)
            for name in before_services
        }

        return DependencyImpact(
            failure_type="service",
            failure_target=service_name,
            nodes_affected=before_services[service_name].providing_nodes,
            links_affected=[],
            services_before={k: v.status for k, v in before_services.items()},
            services_after=after_services,
            newly_degraded_services=[],
            newly_down_services=sorted(hypothetical_down - {service_name}),
        )
