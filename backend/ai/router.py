"""
backend/ai/router.py

FastAPI router for the AI + Prediction track. Updated for the real schema
(v2): detect_anomalies()/predict_failures() now need central_node_id, and
there are two new link-level endpoints since links have independent
telemetry now (LinkAnomalyDetector in anomaly_detection.py).

Kept as its own APIRouter, not appended into backend/main.py -- confirmed
with Aakash this matches the pattern he's using for his own router too.
To wire in (already done once, only needed again if main.py's include
line is ever lost):

    from backend.ai.router import router as ai_router
    app.include_router(ai_router)

NOT EXECUTED HERE: fastapi isn't installed in this sandbox and it has no
network access. Standard FastAPI conventions, but run test_router.py
locally before relying on it.
"""

from fastapi import APIRouter

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.ai.failure_prediction import TrendFailurePredictor, predict_failures
from backend.ai.telemetry_sim import SyntheticTelemetryGenerator

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Dev-only telemetry source until Akshata's real feed is wired up. Swap this
# for the real feed call once it exists -- everything downstream just takes
# whatever TelemetrySnapshot it's given.
_dev_generator = SyntheticTelemetryGenerator(num_leaves=8, seed=None)
_central_id = _dev_generator.central_node_id

# Predictor needs history across calls, so it's module-level, not per-request.
_predictor = TrendFailurePredictor(central_node_id=_central_id)


@router.get("/anomalies")
def get_anomalies():
    """Feature 1: AI Anomaly Detection, node-level."""
    snapshot = _dev_generator.generate_snapshot()
    return {"results": detect_anomalies(snapshot, central_node_id=_central_id)}


@router.get("/link-anomalies")
def get_link_anomalies():
    """Feature 1: AI Anomaly Detection, link-level (new in v2 -- link_down
    / link_congestion can now be told apart from a node actually failing)."""
    snapshot = _dev_generator.generate_snapshot()
    return {"results": detect_link_anomalies(snapshot)}


@router.get("/failure-predictions")
def get_failure_predictions():
    """Feature 2: Predictive Failure Detection. Trend-based failure
    probability per node, built from accumulated snapshot history."""
    snapshot = _dev_generator.generate_snapshot()
    _predictor.update(snapshot)
    return {"results": predict_failures(_predictor)}


@router.get("/failure-classification")
def get_failure_classification():
    """Feature 3: Failure Classification, node-level."""
    snapshot = _dev_generator.generate_snapshot()
    anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    return {"results": classify_failures(anomalies)}


@router.get("/link-failure-classification")
def get_link_failure_classification():
    """Feature 3: Failure Classification, link-level (new in v2)."""
    snapshot = _dev_generator.generate_snapshot()
    link_anomalies = detect_link_anomalies(snapshot)
    return {"results": classify_link_failures(link_anomalies)}