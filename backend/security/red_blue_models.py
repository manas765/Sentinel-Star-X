from dataclasses import dataclass, field
from typing import List

from .models import NetworkActivitySnapshot


@dataclass
class RedTeamScenarioStep:
    """One simulated attack step — a controlled, predefined snapshot to feed into the pipeline."""
    label: str
    snapshot: NetworkActivitySnapshot


@dataclass
class BlueTeamStepResult:
    step_label: str
    entity_id: str
    risk_score: float
    threat_level: str
    survival_mode_active: bool
    flags: List[str] = field(default_factory=list)


@dataclass
class SimulationReport:
    scenario_name: str
    steps: List[BlueTeamStepResult] = field(default_factory=list)

    @property
    def final_threat_level(self) -> str:
        return self.steps[-1].threat_level if self.steps else "UNKNOWN"

    @property
    def survival_mode_was_triggered(self) -> bool:
        return any(step.survival_mode_active for step in self.steps)