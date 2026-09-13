"""
backend/network/fidelity_calibration.py

Simulation Fidelity Calibration (feature 6.62).

"Measure how closely Digital Twin simulations correspond to observed
network behavior... use the error to improve future simulations."

Honest framing: right now the Digital Twin reads the SAME simulator as
the "real" network, so most fields would trivially match. The one place a
genuine predicted-vs-observed comparison exists today is the Sandbox
(6.5): it forecasts an outcome BEFORE a change is made for real. This
module records that forecast, then - once the same change is actually
applied to the real network (e.g. via TopologyMorpher) - compares the
forecast against what really happened, and reports the error per metric.

This is the actual mechanism the doc asks for; it's just currently
exercised only via sandbox-vs-real-after-applying, since that is the one
place "predicted" and "observed" are legitimately different things here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

_METRICS = ["latency_ms", "packet_loss_pct", "throughput_mbps"]


@dataclass
class FidelityRecord:
    scenario_label: str
    predicted_at: float
    predicted_state: dict
    observed_at: float | None = None
    observed_state: dict | None = None
    error_by_metric: dict = field(default_factory=dict)   # metric -> mean absolute error
    service_impact_match: bool | None = None


class FidelityCalibrator:
    def __init__(self):
        self._records: dict = {}

    def record_prediction(self, scenario_label: str, predicted_state: dict):
        """Call this right after WhatIfSandbox.run_scenario() - store what
        the sandbox forecast before anything real happens."""
        self._records[scenario_label] = FidelityRecord(
            scenario_label=scenario_label,
            predicted_at=time.time(),
            predicted_state=predicted_state,
        )

    def record_observed(self, scenario_label: str, observed_state: dict):
        """Call this after the same change was actually applied to the
        real network. Computes and stores the error against the earlier
        prediction. Returns None if no prediction was ever recorded for
        this label - never fabricates a comparison out of thin air."""
        record = self._records.get(scenario_label)
        if record is None:
            return None

        record.observed_at = time.time()
        record.observed_state = observed_state

        predicted_nodes = {n["node_id"]: n for n in record.predicted_state["nodes"]}
        observed_nodes = {n["node_id"]: n for n in observed_state["nodes"]}
        common_ids = set(predicted_nodes) & set(observed_nodes)

        errors = {}
        for metric in _METRICS:
            diffs = [
                abs(predicted_nodes[nid][metric] - observed_nodes[nid][metric])
                for nid in common_ids
            ]
            errors[metric] = round(sum(diffs) / len(diffs), 4) if diffs else None
        record.error_by_metric = errors

        predicted_down = {n for n in predicted_nodes if predicted_nodes[n]["status"] == "down"}
        observed_down = {n for n in observed_nodes if observed_nodes[n]["status"] == "down"}
        record.service_impact_match = predicted_down == observed_down

        return record

    def get_record(self, scenario_label: str):
        return self._records.get(scenario_label)

    def overall_report(self) -> dict:
        """Aggregate error across every scenario that has BOTH a
        prediction and an observation - scenarios still pending
        real-world application are excluded, not counted as zero-error."""
        completed = [r for r in self._records.values() if r.observed_state is not None]
        if not completed:
            return {"scenarios_calibrated": 0, "note": "No completed predicted-vs-observed pairs yet."}

        avg_errors = {}
        for metric in _METRICS:
            values = [r.error_by_metric[metric] for r in completed if r.error_by_metric.get(metric) is not None]
            avg_errors[metric] = round(sum(values) / len(values), 4) if values else None

        match_rate = sum(1 for r in completed if r.service_impact_match) / len(completed)

        return {
            "scenarios_calibrated": len(completed),
            "avg_error_by_metric": avg_errors,
            "service_impact_match_rate": round(match_rate, 3),
        }
