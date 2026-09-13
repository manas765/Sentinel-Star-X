"""
backend/network/router.py

FastAPI router for the Network + Digital Twin track (Akshata).

Follows the same per-track APIRouter pattern already used in
backend/ai/router.py, so this doesn't turn backend/main.py into a
merge-conflict hotspot across four people's tracks. To wire it in,
backend/main.py needs (once):

    from backend.network.router import router as network_router
    app.include_router(network_router)

NOTE: main.py currently has its own hardcoded GET /api/network/status
route already. FastAPI will use whichever route is registered first if
both exist, so that hardcoded one should be deleted from main.py once
this router is wired in - otherwise this real one never actually gets
hit. Flagging rather than silently deleting someone else's route.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.digital_twin.drift import DriftDetector
from backend.digital_twin.twin import DigitalTwin
from backend.health.engine import HealthEngine
from backend.network.cascade_predictor import CascadePredictor
from backend.network.critical_path import CriticalPathProtector
from backend.network.dependency_analyzer import DependencyAnalyzer
from backend.network.min_change_recovery import select_minimum_change
from backend.network.service_graph import ServiceDependencyGraph
from backend.network.simulator import NetworkSimulator
from backend.network.topology_morpher import TopologyMorpher
from backend.network.topology_recommender import TopologyRecommendationEngine

router = APIRouter(prefix="/api/network", tags=["network"])

# Module-level state so it persists across requests (health engine needs
# history for its EMA smoothing, digital twin needs a persistent mirror).
# Swap num_leaves/seed for real deployment config later.
_simulator = NetworkSimulator(num_leaves=8, seed=None)
_twin = DigitalTwin(_simulator)
_health_engine = HealthEngine()
_cascade_predictor = CascadePredictor()
_service_graph = ServiceDependencyGraph()
_critical_path_protector = CriticalPathProtector()
_dependency_analyzer = DependencyAnalyzer(_twin)
_drift_detector = DriftDetector()
_topology_recommender = TopologyRecommendationEngine()
_topology_morpher = TopologyMorpher(_simulator)
_latest_candidates: list = []  # cached so /approve can reference by index


def _sync_and_score() -> dict:
    """Advance one tick, recompute health scores, return the merged state."""
    snapshot = _twin.sync()
    scores = _health_engine.score_snapshot(snapshot.nodes)
    for node_id, score in scores.items():
        _twin.attach_health_score(node_id, score)
    return _twin.get_state()


@router.get("/status")
def network_status():
    """Real network status - replaces the hardcoded values in main.py."""
    state = _sync_and_score()
    nodes = state["nodes"]
    healthy = sum(1 for n in nodes if n["status"] == "up")
    degraded = sum(1 for n in nodes if n["status"] == "degraded")
    failed = sum(1 for n in nodes if n["status"] == "down")
    avg_health = round(sum(n["health_score"] or 0 for n in nodes) / len(nodes), 2) if nodes else 0.0

    return {
        "total_nodes": len(nodes),
        "healthy_nodes": healthy,
        "degraded_nodes": degraded,
        "failed_nodes": failed,
        "overall_health": avg_health,
        "topology_version": state["topology_version"],
        "tick": state["tick"],
    }


@router.get("/state")
def full_state():
    """Full mirrored Digital Twin state - topology + telemetry + health/trust/security overlays."""
    return _sync_and_score()


@router.get("/cascade-prediction")
def cascade_prediction():
    """Feature 6.17: cascade probability, likely affected nodes/services, preventive recommendation."""
    state = _sync_and_score()
    predictions = _cascade_predictor.predict(state)
    return {"results": [p.__dict__ for p in predictions]}


@router.get("/service-graph")
def service_graph():
    """Feature 6.19: per-service status (up/degraded/down) derived from device health, not just device status."""
    state = _sync_and_score()
    statuses = _service_graph.compute_status(state)
    return {"services": {name: s.__dict__ for name, s in statuses.items()}}


@router.get("/critical-paths")
def critical_paths():
    """Feature 6.20: paths serving critical services, and whether a redundant path exists."""
    state = _sync_and_score()
    paths = _critical_path_protector.get_critical_paths(state)
    return {"results": [p.__dict__ for p in paths]}


@router.get("/dependency-analysis/node/{node_id}")
def dependency_analysis_node(node_id: str):
    """Feature 6.49: downstream service/node impact if this node fails. Simulated in a sandbox fork - never touches the real network."""
    _sync_and_score()
    impact = _dependency_analyzer.analyze_node_failure(node_id)
    return impact.__dict__


@router.get("/dependency-analysis/link/{link_id}")
def dependency_analysis_link(link_id: str):
    """Feature 6.49: downstream impact if this link fails."""
    _sync_and_score()
    impact = _dependency_analyzer.analyze_link_failure(link_id)
    return impact.__dict__


@router.get("/dependency-analysis/service/{service_name}")
def dependency_analysis_service(service_name: str):
    """Feature 6.49: which other services would go down if this one did (dependency-chain walk, no simulation needed)."""
    _sync_and_score()
    impact = _dependency_analyzer.analyze_service_failure(service_name)
    return impact.__dict__


@router.get("/drift")
def drift():
    """Feature 6.57: compares the real twin against a forked sandbox twin one tick later.
    See drift.py's docstring for why this isn't real-vs-twin yet - there's only one data source so far."""
    _sync_and_score()
    forked = _twin.fork()
    forked.sync()
    report = _drift_detector.compare(_twin.get_state(), forked.get_state())
    return report.__dict__


@router.get("/topology-recommendations")
def topology_recommendations():
    """Feature 6.61: candidate topology changes for currently-unprotected critical nodes,
    sorted cheapest first. None are policy-approved yet - see the /approve endpoint."""
    global _latest_candidates
    state = _sync_and_score()
    _latest_candidates = _topology_recommender.generate_candidates(state)
    return {
        "candidates": [
            {"index": i, **{k: (v.value if hasattr(v, "value") else v) for k, v in c.__dict__.items()}}
            for i, c in enumerate(_latest_candidates)
        ]
    }


@router.post("/topology-recommendations/{index}/approve")
def approve_candidate(index: int, passed: bool = True, notes: str = ""):
    """Policy/Security track calls this (or a human does, during testing) to
    mark a candidate reviewed. Nothing gets applied without this."""
    if index < 0 or index >= len(_latest_candidates):
        return {"error": f"No candidate at index {index}. Call GET /topology-recommendations first."}
    candidate = _latest_candidates[index]
    _topology_recommender.mark_policy_result(candidate, passed=passed, notes=notes)
    return {"index": index, "policy_checked": candidate.policy_checked, "policy_notes": candidate.policy_notes}


@router.post("/topology-morph/apply")
def apply_morph():
    """Feature 6.24/6.25: pick the cheapest policy-approved candidate and apply it (creates real links)."""
    picked = select_minimum_change(_latest_candidates)
    if picked is None:
        return {"error": "No policy-approved candidate available. Approve one first via /approve."}
    episode = _topology_morpher.apply(picked)
    return {
        "morph_state": _topology_morpher.state.value,
        "change_type": episode.candidate.change_type.value,
        "links_added": episode.added_link_ids,
    }


@router.post("/topology-morph/revert")
def revert_morph():
    """Removes exactly the links the active morph episode added, returns to STAR."""
    try:
        _topology_morpher.revert()
    except RuntimeError as e:
        return {"error": str(e)}
    return {"morph_state": _topology_morpher.state.value}


@router.get("/topology-morph/status")
def morph_status():
    episode = _topology_morpher.active_episode
    return {
        "morph_state": _topology_morpher.state.value,
        "active_episode": None if episode is None else {
            "change_type": episode.candidate.change_type.value,
            "links_added": episode.added_link_ids,
        },
    }