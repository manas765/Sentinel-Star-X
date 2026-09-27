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
from backend.ai.benchmarking_engine import run_benchmark
from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.ai.failure_prediction import TrendFailurePredictor, predict_failures
from backend.ai.explainable_ai import explain_network_state
from backend.ai.incident_replay import IncidentReplayBuffer
from backend.ai.graph_generation import generate_graph
from backend.ai.resilience_index import calculate_resilience_index
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.ai.telemetry_sim import SyntheticTelemetryGenerator
from backend.ai.network_forecast import forecast_network_weather
from backend.ai.risk_map import generate_risk_map
from backend.ai.recovery_confidence import evaluate_recovery_confidence
from backend.ai.network_copilot import QueryIntent, ask_copilot
from backend.ai.whatif_engine import simulate_what_if

router = APIRouter(prefix="/api/ai", tags=["ai"])

_dev_generator = SyntheticTelemetryGenerator(num_leaves=8, seed=None)
_central_id = _dev_generator.central_node_id
_predictor = TrendFailurePredictor(central_node_id=_central_id)
_incident_buffer = IncidentReplayBuffer()


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

@router.get("/explain")
def get_explanations():
    """Feature 8 (global #37): Explainable AI. Human-readable summaries
    for every anomalous node/link, distinguishing root causes from
    downstream symptoms."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    results = explain_network_state(node_anomalies, link_anomalies, _dev_generator.topology, _central_id)
    return {"results": results}

@router.get("/tick")
def run_and_record_tick():
    """Feature 9 (global #38): Incident Replay -- driver endpoint. Runs one
    full analysis pass (Features 1, 3, 4, 8) and records it into the
    rolling incident buffer. Call this on whatever cadence you want ticks
    recorded (e.g. a poller); /incidents and /incidents/{id}/replay read
    from what's been recorded here."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    classifications = classify_failures(node_anomalies)
    link_classifications = classify_link_failures(link_anomalies)
    root_causes = analyze_root_causes(node_anomalies, link_anomalies, _dev_generator.topology, _central_id)
    explanations = explain_network_state(node_anomalies, link_anomalies, _dev_generator.topology, _central_id)

    _incident_buffer.record(
        timestamp=snapshot.timestamp,
        node_anomalies=node_anomalies,
        link_anomalies=link_anomalies,
        classifications=classifications,
        link_classifications=link_classifications,
        root_causes=root_causes,
        explanations=explanations,
    )
    return {"recorded": True, "has_anomaly": any(r["is_anomalous"] for r in node_anomalies + link_anomalies)}


@router.get("/incidents")
def get_incidents():
    """Feature 9: list every incident recorded so far (open or closed)."""
    return {"results": _incident_buffer.list_incidents()}


@router.get("/incidents/{incident_id}/replay")
def get_incident_replay(incident_id: int):
    """Feature 9: full tick-by-tick sequence for one incident."""
    return {"results": _incident_buffer.replay(incident_id)}

@router.get("/forecast")
def get_forecast(horizon_ticks: int = 10):
    """Feature 10 (global #40): Network Forecast / Network Weather.
    Projects the resilience score forward based on current per-node
    prediction trends, plus a "weather" label and which nodes are
    predicted to actually fail within the horizon."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    _predictor.update(snapshot)
    predictions = predict_failures(_predictor)
    resilience = calculate_resilience_index(
        node_anomalies, link_anomalies, predictions, _dev_generator.topology, _central_id
    )
    return forecast_network_weather(predictions, resilience["score"], horizon_ticks=horizon_ticks)

@router.get("/risk-map")
def get_risk_map():
    """Feature 11 (global #41): Network Risk Map. Same layout as /graph
    but colored by PREDICTED risk (Feature 2) instead of current severity."""
    snapshot = _dev_generator.generate_snapshot()
    link_anomalies = detect_link_anomalies(snapshot)
    _predictor.update(snapshot)
    predictions = predict_failures(_predictor)
    return generate_risk_map(_dev_generator.topology, predictions, link_anomalies, _central_id)

@router.get("/recovery-confidence")
def get_recovery_confidence():
    """Feature 12 (global #44): Recovery Confidence. Confidence in the
    diagnosis backing a recovery decision, not confidence in a specific
    recovery strategy -- see recovery_confidence.py's interface flag re:
    whether Aakash's Decision Engine needs the latter instead."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    results = evaluate_recovery_confidence(node_anomalies, link_anomalies, _dev_generator.topology, _central_id)
    return {"results": results}

@router.get("/copilot")
def get_copilot_answer(intent: str = "status_summary", horizon_ticks: int = 10):
    """Feature 13 (global #51): AI Network Copilot. Predefined query
    intents (status_summary, whats_wrong, what_to_fix_first,
    resilience_score, forecast, at_risk_soon) -- see network_copilot.py's
    scope flag re: free-text parsing needing an LLM key that isn't set up."""
    snapshot = _dev_generator.generate_snapshot()
    node_anomalies = detect_anomalies(snapshot, central_node_id=_central_id)
    link_anomalies = detect_link_anomalies(snapshot)
    _predictor.update(snapshot)
    predictions = predict_failures(_predictor)
    return ask_copilot(
        QueryIntent(intent), node_anomalies, link_anomalies, predictions,
        _dev_generator.topology, _central_id, horizon_ticks=horizon_ticks
    )

@router.get("/whatif")
def get_whatif(scenario: str = "node_down", target: str = "leaf-0"):
    """Feature 14 (global #52): Natural-Language What-If. Structured
    scenario+target for now -- see whatif_engine.py's two scope flags
    (LLM key, and overlap with Akshata's Sandbox/What-If Lab)."""
    return simulate_what_if(_dev_generator, scenario, target)