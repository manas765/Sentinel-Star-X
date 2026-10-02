"""
backend/ai/benchmarking_engine.py

Feature 5/16 (global #34): Benchmarking Engine.

Per your call: benchmarks THIS TRACK'S OWN AI detectors (Features 1, 3, 4)
against known test scenarios built from the synthetic generator's labeled
anomaly injection -- since we know exactly which node/link was made
anomalous and what type, we get ground truth for free, no external labeled
dataset needed.

Scope: node/link anomaly detection (precision/recall/F1/false-positive
rate/latency), failure classification (category accuracy), and root cause
analysis (correct target attribution). Failure Prediction (Feature 2)'s
trend/lead-time isn't benchmarked here -- the synthetic generator injects
anomalies abruptly rather than ramping gradually, so there isn't a
meaningful "early warning" signal to score yet. Revisit once there's real
historical data with gradual degradation in it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.failure_classification import (
    FailureCategory,
    classify_failures,
    classify_link_failures,
)
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator

EXPECTED_CATEGORY = {
    AnomalyType.NODE_DOWN: FailureCategory.NODE_DOWN,
    AnomalyType.NODE_OVERLOAD: FailureCategory.NODE_OVERLOAD,
    AnomalyType.LATENCY_SPIKE: FailureCategory.LATENCY_DEGRADATION,
    AnomalyType.PACKET_LOSS: FailureCategory.PACKET_LOSS,
    AnomalyType.LINK_DOWN: FailureCategory.LINK_DOWN,
    AnomalyType.LINK_CONGESTION: FailureCategory.LINK_CONGESTION,
}

NODE_ANOMALY_TYPES = [
    AnomalyType.NODE_DOWN,
    AnomalyType.NODE_OVERLOAD,
    AnomalyType.LATENCY_SPIKE,
    AnomalyType.PACKET_LOSS,
]
LINK_ANOMALY_TYPES = [AnomalyType.LINK_DOWN, AnomalyType.LINK_CONGESTION]


@dataclass
class DetectionMetrics:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return round(self.true_positives / denom, 3) if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return round(self.true_positives / denom, 3) if denom else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return round(2 * p * r / (p + r), 3) if (p + r) else 0.0

    @property
    def false_positive_rate(self) -> float:
        denom = self.false_positives + self.true_negatives
        return round(self.false_positives / denom, 3) if denom else 0.0

    def to_dict(self) -> dict:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positive_rate": self.false_positive_rate,
        }


@dataclass
class BenchmarkReport:
    node_detection: DetectionMetrics
    link_detection: DetectionMetrics
    classification_accuracy: float
    classification_samples: int
    root_cause_attribution_accuracy: float
    root_cause_samples: int
    avg_detection_latency_ms: float
    scenarios_run: int

    def to_dict(self) -> dict:
        return {
            "node_detection": self.node_detection.to_dict(),
            "link_detection": self.link_detection.to_dict(),
            "classification_accuracy": self.classification_accuracy,
            "classification_samples": self.classification_samples,
            "root_cause_attribution_accuracy": self.root_cause_attribution_accuracy,
            "root_cause_samples": self.root_cause_samples,
            "avg_detection_latency_ms": self.avg_detection_latency_ms,
            "scenarios_run": self.scenarios_run,
        }


class BenchmarkingEngine:
    """Runs the detection/classification/RCA pipeline against synthetic
    scenarios with known ground truth, and scores it."""

    def __init__(self, num_leaves: int = 5, trials_per_scenario: int = 3):
        self.num_leaves = num_leaves
        self.trials_per_scenario = trials_per_scenario

    def run(self) -> BenchmarkReport:
        node_metrics = DetectionMetrics()
        link_metrics = DetectionMetrics()
        classification_correct = 0
        classification_total = 0
        rca_correct = 0
        rca_total = 0
        latencies_ms = []

        for seed in range(self.trials_per_scenario):
            self._score_scenario(
                seed=1000 + seed,
                anomaly=None,
                target=None,
                is_link=False,
                node_metrics=node_metrics,
                link_metrics=link_metrics,
                latencies_ms=latencies_ms,
            )

        for idx, anomaly in enumerate(NODE_ANOMALY_TYPES):
            for trial in range(self.trials_per_scenario):
                seed = idx * 100 + trial
                target = f"leaf-{trial % self.num_leaves}"
                c_correct, c_total, r_correct, r_total = self._score_scenario(
                    seed=seed,
                    anomaly=anomaly,
                    target=target,
                    is_link=False,
                    node_metrics=node_metrics,
                    link_metrics=link_metrics,
                    latencies_ms=latencies_ms,
                )
                classification_correct += c_correct
                classification_total += c_total
                rca_correct += r_correct
                rca_total += r_total

        for idx, anomaly in enumerate(LINK_ANOMALY_TYPES):
            for trial in range(self.trials_per_scenario):
                seed = 1000 + idx * 100 + trial
                gen = SyntheticTelemetryGenerator(num_leaves=self.num_leaves, seed=seed)
                target = gen.topology.links[trial % len(gen.topology.links)].link_id
                c_correct, c_total, r_correct, r_total = self._score_scenario(
                    seed=seed,
                    anomaly=anomaly,
                    target=target,
                    is_link=True,
                    node_metrics=node_metrics,
                    link_metrics=link_metrics,
                    latencies_ms=latencies_ms,
                    generator=gen,
                )
                classification_correct += c_correct
                classification_total += c_total
                rca_correct += r_correct
                rca_total += r_total

        scenarios_run = (
            self.trials_per_scenario
            + len(NODE_ANOMALY_TYPES) * self.trials_per_scenario
            + len(LINK_ANOMALY_TYPES) * self.trials_per_scenario
        )

        return BenchmarkReport(
            node_detection=node_metrics,
            link_detection=link_metrics,
            classification_accuracy=(
                round(classification_correct / classification_total, 3) if classification_total else 1.0
            ),
            classification_samples=classification_total,
            root_cause_attribution_accuracy=(
                round(rca_correct / rca_total, 3) if rca_total else 1.0
            ),
            root_cause_samples=rca_total,
            avg_detection_latency_ms=(
                round(sum(latencies_ms) / len(latencies_ms), 3) if latencies_ms else 0.0
            ),
            scenarios_run=scenarios_run,
        )

    def _score_scenario(
        self,
        seed: int,
        anomaly: Optional[AnomalyType],
        target: Optional[str],
        is_link: bool,
        node_metrics: DetectionMetrics,
        link_metrics: DetectionMetrics,
        latencies_ms: list,
        generator: Optional[SyntheticTelemetryGenerator] = None,
    ):
        gen = generator or SyntheticTelemetryGenerator(num_leaves=self.num_leaves, seed=seed)
        snapshot = gen.generate_snapshot(anomaly=anomaly, anomaly_target=target)

        start = time.perf_counter()
        node_results = detect_anomalies(snapshot, central_node_id=gen.central_node_id)
        link_results = detect_link_anomalies(snapshot)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed_ms)

        for r in node_results:
            expected_anomalous = (not is_link) and anomaly is not None and r["node_id"] == target
            self._update_metrics(node_metrics, predicted=r["is_anomalous"], expected=expected_anomalous)

        for r in link_results:
            expected_anomalous = is_link and anomaly is not None and r["link_id"] == target
            self._update_metrics(link_metrics, predicted=r["is_anomalous"], expected=expected_anomalous)

        c_correct = c_total = r_correct = r_total = 0
        if anomaly is not None:
            expected_category = EXPECTED_CATEGORY[anomaly]
            if is_link:
                classified = classify_link_failures(link_results)
                actual = next((c for c in classified if c["link_id"] == target), None)
            else:
                classified = classify_failures(node_results)
                actual = next((c for c in classified if c["node_id"] == target), None)
            if actual is not None:
                c_total = 1
                c_correct = int(actual["category"] == expected_category.value)

            rca_results = analyze_root_causes(node_results, link_results, gen.topology, gen.central_node_id)
            r_total = 1
            r_correct = int(any(rc["root_cause_id"] == target for rc in rca_results))

        return c_correct, c_total, r_correct, r_total

    @staticmethod
    def _update_metrics(metrics: DetectionMetrics, predicted: bool, expected: bool) -> None:
        if predicted and expected:
            metrics.true_positives += 1
        elif predicted and not expected:
            metrics.false_positives += 1
        elif not predicted and expected:
            metrics.false_negatives += 1
        else:
            metrics.true_negatives += 1


def run_benchmark(num_leaves: int = 5, trials_per_scenario: int = 3) -> dict:
    """Convenience entry point. Returns JSON-able dict."""
    engine = BenchmarkingEngine(num_leaves=num_leaves, trials_per_scenario=trials_per_scenario)
    return engine.run().to_dict()