"""
backend/digital_twin/sandbox.py

Digital Twin Sandbox / What-If Lab (feature 6.5).

Flow (per the master doc):
  REAL NETWORK -> DIGITAL TWIN -> SIMULATE FAILURE/CHANGE
  -> TEST STRATEGY A/B/C -> COMPARE -> SELECT -> APPLY TO NETWORK

This module handles everything up to COMPARE. SELECT / APPLY belongs to
the recovery/decision modules (6.21 Recovery Strategy Simulator, 6.22
Multi-Objective Decision Engine) - the sandbox's job is only to run a
scenario in isolation and report what happened, never to touch the real
network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.digital_twin.twin import DigitalTwin


@dataclass
class ScenarioResult:
    label: str
    ticks_run: int
    final_state: dict
    nodes_down: list
    links_down: list


class WhatIfSandbox:
    def __init__(self, real_twin: DigitalTwin):
        self.real_twin = real_twin

    def run_scenario(self, label: str, apply_changes, ticks: int = 5, seed: int | None = None) -> ScenarioResult:
        """
        apply_changes: a callable(forked_simulator) -> None. Mutate the
        forked network here (fail_node, fail_link, set_traffic_multiplier,
        etc.) - it's a throwaway copy, so nothing here touches the real
        network. Example:

            sandbox.run_scenario(
                "kill leaf-2",
                lambda sim: sim.fail_node("leaf-2"),
            )
        """
        forked_twin = self.real_twin.fork(seed=seed)
        apply_changes(forked_twin.source)

        for _ in range(ticks):
            forked_twin.sync()

        state = forked_twin.get_state()
        nodes_down = [n["node_id"] for n in state["nodes"] if n["status"] == "down"]
        links_down = [l["link_id"] for l in state["links"] if l["status"] == "down"]

        return ScenarioResult(
            label=label,
            ticks_run=ticks,
            final_state=state,
            nodes_down=nodes_down,
            links_down=links_down,
        )

    def compare(self, results: list) -> dict:
        """Simple side-by-side comparison. The actual strategy-picking
        logic (weighing cost/downtime/risk) belongs to the Multi-Objective
        Decision Engine (6.22) - this just lays the outcomes side by side."""
        return {
            r.label: {
                "nodes_down": len(r.nodes_down),
                "links_down": len(r.links_down),
                "down_node_ids": r.nodes_down,
            }
            for r in results
        }
