"""
backend/ai/failure_prediction.py

Feature 2/16 (global #7): Predictive Failure Detection.

Approach: mirrors Feature 1's hybrid pattern -- a lightweight trend-based
heuristic now (extrapolates the anomaly score history Feature 1 already
computes, tick over tick), a trained time-series model swappable in later
behind the same interface.

Assumption: predicts off AnomalyDetector's per-tick score history, not raw
telemetry directly -- so it inherits every assumption already flagged in
anomaly_detection.py and telemetry_sim.py. No new schema guesses here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from backend.ai.anomaly_detection import AnomalyDetector, BaseAnomalyDetector


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
    def update(self, snapshot: list) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(self) -> list:
        raise NotImplementedError


class TrendFailurePredictor(BaseFailurePredictor):
    """
    Keeps a rolling window of each node's anomaly score (from Feature 1) and
    extrapolates the trend with a simple linear fit. If a node's score is
    climbing, projects forward to estimate how many ticks until it crosses
    the failure threshold.

    window_size: how many recent ticks to look at.
    failure_threshold: score at/above which a node is considered failed.
    """

    def __init__(
        self,
        anomaly_detector: Optional[BaseAnomalyDetector] = None,
        window_size: int = 10,
        failure_threshold: float = 0.85,
    ):
        self.detector = anomaly_detector or AnomalyDetector()
        self.window_size = window_size
        self.failure_threshold = failure_threshold
        self._history: dict = {}  # node_id -> deque[float]

    def update(self, snapshot: list) -> None:
        """Feed one tick's telemetry snapshot in. Call this once per tick
        as new data arrives, before calling predict()."""
        results = self.detector.detect(snapshot)
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


# Active predictor implementation. Swap this line to plug in a trained
# time-series model later -- every caller importing FailurePredictor from
# this module is unaffected.
FailurePredictor = TrendFailurePredictor


def predict_failures(predictor: TrendFailurePredictor) -> list:
    """Convenience entry point. Returns JSON-able list[dict]."""
    return [p.to_dict() for p in predictor.predict()]