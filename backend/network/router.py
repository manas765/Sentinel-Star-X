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

from backend.digital_twin.twin import DigitalTwin
from backend.health.engine import HealthEngine
from backend.network.cascade_predictor import CascadePredictor
from backend.network.service_graph import ServiceDependencyGraph
from backend.network.simulator import NetworkSimulator

router = APIRouter(prefix="/api/network", tags=["network"])

# Module-level state so it persists across requests (health engine needs
# history for its EMA smoothing, digital twin needs a persistent mirror).
# Swap num_leaves/seed for real deployment config later.
_simulator = NetworkSimulator(num_leaves=8, seed=None)
_twin = DigitalTwin(_simulator)
_health_engine = HealthEngine()
_cascade_predictor = CascadePredictor()
_service_graph = ServiceDependencyGraph()


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
