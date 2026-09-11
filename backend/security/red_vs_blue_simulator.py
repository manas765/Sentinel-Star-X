from typing import List

from .anomaly_detector import SecurityAnomalyDetector
from .critical_service_protection import CriticalServiceProtection
from .red_blue_models import BlueTeamStepResult, RedTeamScenarioStep, SimulationReport
from .survival_mode_manager import SurvivalModeManager
from .threat_level_manager import ThreatLevelManager


class RedVsBlueSimulator:
    """
    Runs a predefined Red Team scenario step-by-step through the real
    Blue Team pipeline (anomaly detection -> threat level -> survival mode),
    producing a report of how the defenses responded at each stage.
    This is a controlled simulation using scripted, sandboxed data only.
    """

    def __init__(self) -> None:
        self.detector = SecurityAnomalyDetector()
        self.threat_manager = ThreatLevelManager()
        self.critical_protection = CriticalServiceProtection()
        self.survival_manager = SurvivalModeManager(self.critical_protection)

    def run_scenario(self, scenario_name: str, steps: List[RedTeamScenarioStep]) -> SimulationReport:
        report = SimulationReport(scenario_name=scenario_name)
        entity_levels = {}

        for step in steps:
            assessment = self.detector.assess(step.snapshot)
            threat_state = self.threat_manager.update(
                step.snapshot.entity_id,
                risk_score=assessment.risk_score,
                reason=f"red team step: {step.label}",
            )
            entity_levels[step.snapshot.entity_id] = threat_state.level
            survival_state = self.survival_manager.update(entity_levels)

            report.steps.append(
                BlueTeamStepResult(
                    step_label=step.label,
                    entity_id=step.snapshot.entity_id,
                    risk_score=assessment.risk_score,
                    threat_level=threat_state.level.name,
                    survival_mode_active=survival_state.is_active,
                    flags=assessment.flags,
                )
            )

        return report