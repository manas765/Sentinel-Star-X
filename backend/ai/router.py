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

from backend.ai.root_cause_analysis import analyze_root_causes

from backend.ai.benchmarking_engine import run_benchmark

from backend.ai.resilience_index import calculate_resilience_index

from backend.ai.graph_generation import generate_graph
"""
from fastapi import APIRouter

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.ai.failure_prediction import TrendFailurePredictor, predict_failures
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.ai.telemetry_sim import SyntheticTelemetryGenerator

router = APIRouter(prefix="/api/ai", tags=["ai"])

_dev_generator = SyntheticTelemetryGenerator(num_leaves=8, seed=None)
_central_id = _dev_generator.central_node_id
_predictor = TrendFailurePredictor(central_node_id=_central_id)


@router.get("/anomalies")
def get_anomalies():
    """Feature 1: AI Anomaly Detection, node-level."""
    snapshot = _dev_generator.generate_snapshot()
    return {"results": detect_anomalies(snapshot, central_node_id=_central_id)}


@router.get("/link-anomalies")
def get_link_anomalies():
    """Feature 1: AI Anomaly Detection, link-level."""
    snapshot = _dev_generator.generate_snapshot()
    return {"results": detect_link_anomalies(snapshot)}


@router.get("/failure-predictions")
def get_failure_predictions():
    """Feature 2: Predictive Failure Detection."""
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
    """Feature 3: Failure Classification, link-level."""
    snapshot = _dev_generator.generate_snapshot()
    link_anomalies = detect_link_anomalies(snapshot)
    return {"results": classify_link_failures(link_anomalies)}


@router.get("/root-cause-analysis")
def get_root_cause_analysis():
    """Feature 4: Root Cause Analysis."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    results = analyze_root_causes(node_anomalies, link_anomalies, _dev_generator.topology, _central_id)
    return {"results": results}

@router.get("/benchmark")
def get_benchmark():
    """Feature 5: Benchmarking Engine. Scores Features 1/3/4 against
    synthetic scenarios with known ground truth. Slower than the other
    endpoints (runs ~35 scenarios per call) -- fine for occasional use,
    not meant to be polled."""
    return run_benchmark()

@router.get("/resilience-index")
def get_resilience_index():
    """Feature 6: SENTINEL Resilience Index. Composite 0-100 score from
    node/link health, predicted failure risk, and cascading-failure penalty."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    _predictor.update(snapshot)
    predictions = predict_failures(_predictor)
    return calculate_resilience_index(
        node_anomalies, link_anomalies, predictions, _dev_generator.topology, _central_id
    )

@router.get("/graph")
def get_graph():
    """Feature 6 (global #35): Automatic Graph Generation. Ready-to-render
    node/edge structure with radial layout + severity color coding."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    return generate_graph(_dev_generator.topology, node_anomalies, link_anomalies, _central_id)