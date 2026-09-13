"""
backend/network/topology_recommender.py

Topology Recommendation Engine (feature 6.61).

Generates candidate topology changes for nodes/services that currently
lack a redundant path (per CriticalPathProtector), scored by a transparent
cost heuristic. The doc explicitly says its illustrative cost numbers
(Full Mesh=87, Partial Mesh=24, Backup Star=12) are placeholders and "real
values must come from the project's cost model" - so this IS that cost
model, not a re-use of the placeholder numbers. It's a simple, documented
heuristic (more links + more affected nodes + riskier change type = higher
cost), meant to be replaced/tuned once you have real deployment data, not
presented as calibrated truth.

Per the doc: "Recommendations must pass policy and security checks before
execution." This module does NOT make that call - policy_checked stays
None until the Policy/Security track sets it via mark_policy_result().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from backend.network.critical_path import CriticalPathProtector

# Cost model: cost = base_cost_per_type + (new_links * PER_LINK_COST)
#                   + (nodes_affected * PER_NODE_COST)
# Kept as named constants (not magic numbers) so whoever tunes this later
# can see exactly what each dial does.
PER_LINK_COST = 8.0
PER_NODE_COST = 3.0


class ChangeType(str, Enum):
    BACKUP_LINK = "backup_link"                # one redundant link, single node
    BACKUP_SWITCH_ACTIVATION = "backup_switch_activation"
    PARTIAL_MESH_LINK = "partial_mesh_link"     # a few cross-links among leaves
    HYBRID = "hybrid"                           # mix of the above


_BASE_COST = {
    ChangeType.BACKUP_LINK: 4.0,
    ChangeType.BACKUP_SWITCH_ACTIVATION: 10.0,
    ChangeType.PARTIAL_MESH_LINK: 6.0,
    ChangeType.HYBRID: 14.0,
}


@dataclass
class TopologyChangeCandidate:
    change_type: ChangeType
    description: str
    new_links: list           # list of (source_id, target_id) tuples to create
    nodes_affected: list
    change_cost: float
    benefit: str
    policy_checked: bool | None = None   # set externally by Policy/Security track
    policy_notes: str = ""


class TopologyRecommendationEngine:
    def __init__(self):
        self._critical_path_protector = CriticalPathProtector()

    def _cost(self, change_type: ChangeType, new_links: list, nodes_affected: list) -> float:
        return round(
            _BASE_COST[change_type]
            + PER_LINK_COST * len(new_links)
            + PER_NODE_COST * len(nodes_affected),
            2,
        )

    def generate_candidates(self, twin_state: dict) -> list:
        """One or more candidates per critical node that currently lacks
        a redundant path. Each unprotected node gets a cheap single-link
        option and, if more than one unprotected node shares the same
        risk, a partial-mesh option covering several at once."""
        paths = self._critical_path_protector.get_critical_paths(twin_state)
        unprotected = [p for p in paths if not p.has_redundant_path]
        if not unprotected:
            return []

        central_id = next(n["node_id"] for n in twin_state["nodes"] if n["is_central"])
        backup_switch_exists = any(
            n["device_type"] == "backup_switch" for n in twin_state["nodes"]
        )

        candidates = []

        # Option A: cheapest fix per unprotected node - one backup link
        # straight to the central switch's twin path is meaningless (it's
        # already linked there); instead link it to another healthy leaf
        # so it survives losing its own primary link.
        other_leaves = [n["node_id"] for n in twin_state["nodes"] if not n["is_central"]]
        for p in unprotected:
            candidates_for_node = [n for n in other_leaves if n != p.node_id]
            if not candidates_for_node:
                continue
            partner = candidates_for_node[0]
            new_links = [(p.node_id, partner)]
            candidates.append(TopologyChangeCandidate(
                change_type=ChangeType.BACKUP_LINK,
                description=f"Add a backup link from {p.node_id} to {partner} "
                            f"so {p.service} survives losing its primary link to {central_id}.",
                new_links=new_links,
                nodes_affected=[p.node_id, partner],
                change_cost=self._cost(ChangeType.BACKUP_LINK, new_links, [p.node_id, partner]),
                benefit=f"Restores redundancy for {p.service} on {p.node_id}.",
            ))

        # Option B: if 2+ nodes are unprotected, a partial mesh linking all
        # of them together is one combined recommendation, usually cheaper
        # per-node-protected than N separate backup links once N is large.
        if len(unprotected) >= 2:
            unprotected_ids = [p.node_id for p in unprotected]
            new_links = [
                (unprotected_ids[i], unprotected_ids[i + 1])
                for i in range(len(unprotected_ids) - 1)
            ]
            candidates.append(TopologyChangeCandidate(
                change_type=ChangeType.PARTIAL_MESH_LINK,
                description=f"Create a partial mesh among {unprotected_ids} so they "
                            "back each other up instead of each needing its own link.",
                new_links=new_links,
                nodes_affected=unprotected_ids,
                change_cost=self._cost(ChangeType.PARTIAL_MESH_LINK, new_links, unprotected_ids),
                benefit=f"Restores redundancy for {len(unprotected)} nodes in one change.",
            ))

        # Option C: backup switch activation, only offered if one actually
        # exists in the topology - otherwise this would be recommending
        # hardware that isn't there.
        if backup_switch_exists:
            backup_switch_id = next(
                n["node_id"] for n in twin_state["nodes"] if n["device_type"] == "backup_switch"
            )
            new_links = [(p.node_id, backup_switch_id) for p in unprotected]
            affected = [p.node_id for p in unprotected] + [backup_switch_id]
            candidates.append(TopologyChangeCandidate(
                change_type=ChangeType.BACKUP_SWITCH_ACTIVATION,
                description=f"Route all {len(unprotected)} unprotected nodes through "
                            f"the existing backup switch {backup_switch_id}.",
                new_links=new_links,
                nodes_affected=affected,
                change_cost=self._cost(ChangeType.BACKUP_SWITCH_ACTIVATION, new_links, affected),
                benefit="Centralizes redundancy through existing hardware instead of ad-hoc links.",
            ))

        return sorted(candidates, key=lambda c: c.change_cost)

    @staticmethod
    def mark_policy_result(candidate: TopologyChangeCandidate, passed: bool, notes: str = ""):
        candidate.policy_checked = passed
        candidate.policy_notes = notes
