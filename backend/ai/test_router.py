"""
backend/ai/test_router.py

NOT EXECUTED IN THE SANDBOX THAT GENERATED THIS -- fastapi isn't installed
there and it has no network access. Run it in your own venv, where fastapi
is already a dependency since Aakash's using it elsewhere:

    pytest backend/ai/test_router.py -v
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.ai.router import router


def _client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_anomalies_endpoint_returns_results_list():
    client = _client()
    response = client.get("/api/ai/anomalies")
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert isinstance(body["results"], list)
    assert len(body["results"]) > 0
    assert "node_id" in body["results"][0]
    assert "is_anomalous" in body["results"][0]


def test_failure_predictions_endpoint_returns_results_list():
    client = _client()
    response = client.get("/api/ai/failure-predictions")
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert isinstance(body["results"], list)
    assert len(body["results"]) > 0
    assert "failure_probability" in body["results"][0]