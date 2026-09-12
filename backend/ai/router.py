"""
backend/ai/router.py

FastAPI router for the AI + Prediction track. Framework confirmed by
Aakash: FastAPI, app defined in backend/main.py, endpoints are plain
functions returning dicts.

Kept as its own APIRouter instead of adding routes straight into
backend/main.py, so 16 endpoints across this track don't turn a file all
four tracks touch into a merge-conflict hotspot. To wire it in,
backend/main.py needs (once, not per-endpoint):

    from backend.ai.router import router as ai_router
    app.include_router(ai_router)

ASSUMPTION -- flagged, not guessed past: I haven't seen backend/main.py,
so I don't know if per-track routers is what Aakash actually wants, or if
he'd rather every endpoint live directly in main.py like his example.
Confirm before merging this file (see the group reply draft).

NOT EXECUTED HERE: fastapi isn't installed in this sandbox and it has no
network access, so this file is written to standard FastAPI conventions
but not run. Run backend/ai/test_router.py locally (where fastapi is
already installed) to confirm before you PR it.
"""

from fastapi import APIRouter

from backend.ai.anomaly_detection import detect_anomalies
from backend.ai.failure_prediction import TrendFailurePredictor, predict_failures
from backend.ai.telemetry_sim import SyntheticTelemetryGenerator

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Dev-only telemetry source until Akshata's real feed is wired up. Swap this
# for the real feed call once it exists -- nothing downstream needs to change,
# detect_anomalies()/predict_failures() just take whatever snapshot they're given.
_dev_generator = SyntheticTelemetryGenerator(num_leaves=8, seed=None)

# Predictor needs history across calls, so it's module-level, not per-request.
_predictor = TrendFailurePredictor()


@router.get("/anomalies")
def get_anomalies():
    """Feature 1: AI Anomaly Detection. Current anomaly status per node."""
    snapshot = _dev_generator.generate_snapshot()
    return {"results": detect_anomalies(snapshot)}


@router.get("/failure-predictions")
def get_failure_predictions():
    """Feature 2: Predictive Failure Detection. Trend-based failure
    probability per node, built from accumulated snapshot history."""
    snapshot = _dev_generator.generate_snapshot()
    _predictor.update(snapshot)
    return {"results": predict_failures(_predictor)}