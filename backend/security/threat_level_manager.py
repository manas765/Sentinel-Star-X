from typing import Dict

from .threat_level_models import ThreatLevel, ThreatLevelState

# Risk score -> threat level thresholds (uses SecurityAssessment.risk_score, 0.0-1.0)
THREAT_THRESHOLDS = [
    (0.85, ThreatLevel.EMERGENCY),
    (0.65, ThreatLevel.QUARANTINE),
    (0.45, ThreatLevel.RESTRICT),
    (0.25, ThreatLevel.SUSPICIOUS),
    (0.10, ThreatLevel.MONITOR),
    (0.0, ThreatLevel.NORMAL),
]

# Threat level is only allowed to drop by one step at a time, even if the
# risk score suddenly looks calm — this avoids abruptly trusting an entity
# that was just at EMERGENCY.
MAX_DOWNGRADE_STEPS_PER_UPDATE = 1


class ThreatLevelManager:
    """
    Maps ongoing security risk scores to an explainable threat-level ladder.
    Escalation (getting worse) can jump straight to the right level.
    De-escalation (getting better) only steps down one level at a time,
    so recovery is gradual and auditable rather than an instant reset.
    """

    def __init__(self) -> None:
        self._states: Dict[str, ThreatLevelState] = {}

    def get_state(self, entity_id: str) -> ThreatLevelState:
        if entity_id not in self._states:
            self._states[entity_id] = ThreatLevelState(entity_id=entity_id)
        return self._states[entity_id]

    def update(self, entity_id: str, risk_score: float, reason: str = "") -> ThreatLevelState:
        state = self.get_state(entity_id)
        target_level = self._level_for_score(risk_score)

        if target_level >= state.level:
            state.transition_to(
                target_level,
                reason=reason or f"risk score {risk_score:.2f} maps to {target_level.name}",
            )
        elif target_level < state.level:
            stepped_level = ThreatLevel(max(target_level, state.level - MAX_DOWNGRADE_STEPS_PER_UPDATE))
            state.transition_to(
                stepped_level,
                reason=reason or f"risk score {risk_score:.2f} improving, stepping down toward {target_level.name}",
            )

        return state

    def _level_for_score(self, risk_score: float) -> ThreatLevel:
        for threshold, level in THREAT_THRESHOLDS:
            if risk_score >= threshold:
                return level
        return ThreatLevel.NORMAL