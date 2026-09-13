"""
backend/ai/failure_prediction.py

Feature 2/16 (global #7): Predictive Failure Detection.

Updated for the real schema (v2): AnomalyDetector.detect() now needs a
central_node_id, so TrendFailurePredictor takes and stores one too, passing
it through on every update(). Everything else (the trend/slope math) is
unchanged -- it still just tracks Feature 1's score over time, so it
inherits whatever Feature 1 inherited from the schema, nothing new to
guess here.

Approach: mirrors Feature 1's hybrid pattern -- a lightweight trend-based
heuristic now, a trained time-series model swappable in later behind the
same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from backend.ai.anomaly_detection import AnomalyDetector, BaseAnomalyDetector
from backend.telemetry.schema import TelemetrySnapshot


@dataclass
class PredictionResult:
    node_id: str
    failure_probability: float  # 0.0 - 1.0
    trend: str  # "improving" | "stable" | "worsening"
    estimated_ticks_to_failure: Optional[int]  # None if not trending toward failure
    confidence: float  # 0.0 - 1.0, based on how much history we have

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class BaseFailurePredictor(ABC):
    @abstractmethod
    def update(self, snapshot: TelemetrySnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(self) -> list:
        raise NotImplementedError


class TrendFailurePredictor(BaseFailurePredictor):
    """
    Keeps a rolling window of each node's anomaly score (from Feature 1) and
    extrapolates the trend with a simple linear fit.

    central_node_id: passed straight through to the anomaly detector on
    every update() call, since telemetry itself doesn't say which node is
    central anymore -- see anomaly_detection.py.
    window_size: how many recent ticks to look at.
    failure_threshold: score at/above which a node is considered failed.
    """

    def __init__(
        self,
        anomaly_detector: Optional[BaseAnomalyDetector] = None,
        central_node_id: Optional[str] = None,
        window_size: int = 10,
        failure_threshold: float = 0.85,
    ):
        self.detector = anomaly_detector or AnomalyDetector()
        self.central_node_id = central_node_id
        self.window_size = window_size
        self.failure_threshold = failure_threshold
        self._history: dict = {}  # node_id -> deque[float]

    def update(self, snapshot: TelemetrySnapshot) -> None:
        """Feed one tick's telemetry snapshot in. Call this once per tick,
        before calling predict()."""
        results = self.detector.detect(snapshot, central_node_id=self.central_node_id)
        for r in results:
            hist = self._history.setdefault(r.node_id, deque(maxlen=self.window_size))
            hist.append(r.score)

    def predict(self) -> list:
        return [self._predict_node(node_id, hist) for node_id, hist in self._history.items()]

    def _predict_node(self, node_id: str, hist: Deque) -> PredictionResult:
        n = len(hist)
        if n < 2:
            return PredictionResult(
                node_id=node_id,
                failure_probability=hist[-1] if hist else 0.0,
                trend="stable",
                estimated_ticks_to_failure=None,
                confidence=0.0,
            )

        scores = list(hist)
        slope = self._slope(scores)
        current = scores[-1]

        if slope > 0.02:
            trend = "worsening"
        elif slope < -0.02:
            trend = "improving"
        else:
            trend = "stable"

        eta = None
        if slope > 0.001 and current < self.failure_threshold:
            eta = max(1, round((self.failure_threshold - current) / slope))

        probability = min(1.0, max(0.0, current + slope * 3))
        confidence = min(1.0, n / self.window_size)

        return PredictionResult(
            node_id=node_id,
            failure_probability=round(probability, 3),
            trend=trend,
            estimated_ticks_to_failure=eta,
            confidence=round(confidence, 3),
        )

    @staticmethod
    def _slope(values: list) -> float:
        """Simple linear regression slope over evenly spaced points."""
        n = len(values)
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(values) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
        den = sum((x - mean_x) ** 2 for x in xs)
        return num / den if den else 0.0


FailurePredictor = TrendFailurePredictor


def predict_failures(predictor: TrendFailurePredictor) -> list:
    """Convenience entry point. Returns JSON-able list[dict]."""
    return [p.to_dict() for p in predictor.predict()]


def get_failure_risk(predictor: TrendFailurePredictor, node_id: str) -> float:
    """Single-node lookup for Akshata's HealthEngine hook:
    engine.score_node(node_telemetry, predicted_failure_risk=get_failure_risk(predictor, node_id))
    Returns 0.0 if the node has no prediction history yet."""
    for p in predictor.predict():
        if p.node_id == node_id:
            return round(p.failure_probability, 3)
    return 0.0