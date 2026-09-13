"""
backend/ai/test_router.py

NOT EXECUTED IN THE SANDBOX THAT GENERATED THIS -- fastapi isn't installed
there and it has no network access. Run it in your own venv:

    pytest backend/ai/test_router.py -v
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.ai.router import router


def _client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_anomalies_endpoint():
    response = _client().get("/api/ai/anomalies")
    assert response.status_code == 200
    body = response.json()["results"]
    assert isinstance(body, list) and len(body) > 0
    assert "node_id" in body[0] and "is_anomalous" in body[0]


def test_link_anomalies_endpoint():
    response = _client().get("/api/ai/link-anomalies")
    assert response.status_code == 200
    body = response.json()["results"]
    assert isinstance(body, list) and len(body) > 0
    assert "link_id" in body[0] and "is_anomalous" in body[0]


def test_failure_predictions_endpoint():
    response = _client().get("/api/ai/failure-predictions")
    assert response.status_code == 200
    body = response.json()["results"]
    assert isinstance(body, list) and len(body) > 0
    assert "failure_probability" in body[0]


def test_failure_classification_endpoint():
    response = _client().get("/api/ai/failure-classification")
    assert response.status_code == 200
    body = response.json()["results"]
    assert isinstance(body, list) and len(body) > 0
    assert "category" in body[0]


def test_link_failure_classification_endpoint():
    response = _client().get("/api/ai/link-failure-classification")
    assert response.status_code == 200
    body = response.json()["results"]
    assert isinstance(body, list) and len(body) > 0
    assert "category" in body[0]