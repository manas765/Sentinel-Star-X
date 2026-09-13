"""
backend/network/min_change_recovery.py

Minimum-Change Recovery (feature 6.25).

"Choose the smallest topology change that safely solves the incident."
Given a list of TopologyChangeCandidate objects (from
TopologyRecommendationEngine) that all resolve the same incident, pick the
cheapest one that has passed policy/security review. Does NOT decide
policy itself - a candidate with policy_checked=False or None (not yet
reviewed) is never selected, even if it's cheapest, since "safely" is part
of the requirement.
"""

from __future__ import annotations

from backend.network.topology_recommender import TopologyChangeCandidate


def select_minimum_change(
    candidates: list, require_policy_pass: bool = True
) -> TopologyChangeCandidate | None:
    """
    require_policy_pass: if True (default), only candidates with
    policy_checked is True are eligible - candidates that haven't been
    reviewed yet, or failed review, are excluded even if cheaper.
    Set to False only for pre-review "what would we pick" previews.
    """
    eligible = candidates
    if require_policy_pass:
        eligible = [c for c in candidates if c.policy_checked is True]

    if not eligible:
        return None

    # Tie-break: cheapest first, then fewest nodes touched (less blast
    # radius for the same cost), then simplest change type alphabetically
    # for a deterministic result.
    return min(
        eligible,
        key=lambda c: (c.change_cost, len(c.nodes_affected), c.change_type.value),
    )
