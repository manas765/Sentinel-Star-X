from datetime import datetime, timezone
from typing import List

from .incident_report_models import IncidentReport, IncidentReportSection
from .red_blue_models import SimulationReport

_report_counter = 0


def _next_report_id() -> str:
    global _report_counter
    _report_counter += 1
    return f"INC-{_report_counter:04d}"


class IncidentReportGenerator:
    """
    Turns a completed simulation (or, in future, a real incident timeline)
    into a structured, human-readable report — timeline of events, the
    classification, and the final outcome.
    """

    def generate_from_simulation(self, simulation: SimulationReport) -> IncidentReport:
        entity_id = simulation.steps[0].entity_id if simulation.steps else "UNKNOWN"

        timeline_lines = []
        for i, step in enumerate(simulation.steps, start=1):
            flag_text = f" | flags: {', '.join(step.flags)}" if step.flags else ""
            timeline_lines.append(
                f"{i}. [{step.step_label}] risk={step.risk_score:.2f} "
                f"threat_level={step.threat_level} survival_mode={step.survival_mode_active}{flag_text}"
            )

        summary = (
            f"Scenario '{simulation.scenario_name}' on entity '{entity_id}' escalated to "
            f"{simulation.final_threat_level}"
            + (" and triggered Network Survival Mode." if simulation.survival_mode_was_triggered else ".")
        )

        sections = [
            IncidentReportSection(heading="Timeline", content="\n".join(timeline_lines)),
            IncidentReportSection(
                heading="Outcome",
                content=(
                    f"Final threat level: {simulation.final_threat_level}\n"
                    f"Survival mode triggered: {simulation.survival_mode_was_triggered}"
                ),
            ),
            IncidentReportSection(
                heading="Recommended follow-up",
                content=self._recommend_followup(simulation),
            ),
        ]

        return IncidentReport(
            report_id=_next_report_id(),
            entity_id=entity_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            sections=sections,
        )

    def _recommend_followup(self, simulation: SimulationReport) -> str:
        if simulation.final_threat_level in ("QUARANTINE", "EMERGENCY"):
            return "Entity should remain isolated. Manual security review required before any recovery action."
        if simulation.final_threat_level in ("RESTRICT", "SUSPICIOUS"):
            return "Continue monitoring closely. Recovery should go through Security-Gated Recovery approval."
        return "No immediate action required. Continue standard monitoring."