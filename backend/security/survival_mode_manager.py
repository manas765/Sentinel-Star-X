from datetime import datetime, timezone
from typing import Dict, List

from .critical_service_protection import CriticalServiceProtection
from .survival_mode_models import SurvivalModeAssessment, SurvivalModeEvent, SurvivalModeState
from .threat_level_models import ThreatLevel

# Survival mode activates if either condition is met:
CRITICAL_SERVICES_AT_RISK_RATIO = 0.5   # 50%+ of critical services are RESTRICT or worse
NETWORK_WIDE_THREAT_RATIO = 0.4         # 40%+ of all entities are RESTRICT or worse
HIGH_THREAT_FLOOR = ThreatLevel.RESTRICT

# Survival mode only deactivates once things are clearly back to normal,
# with a safety margin below the activation thresholds, to avoid flapping.
DEACTIVATION_SAFETY_MARGIN = 0.5  # both ratios must drop to half the trigger ratio


class SurvivalModeManager:
    """
    Monitors overall network + critical-service health and triggers a
    defensive 'survival mode' posture when the situation is severe enough
    that protecting critical services should take priority over normal
    operation for everything else.
    """

    def __init__(self, critical_service_protection: CriticalServiceProtection) -> None:
        self.critical_service_protection = critical_service_protection
        self.state = SurvivalModeState()

    def assess(self, entity_threat_levels: Dict[str, ThreatLevel]) -> SurvivalModeAssessment:
        critical_ids = self.critical_service_protection.all_critical_ids()
        total_critical = len(critical_ids)
        critical_at_risk = sum(
            1 for eid in critical_ids
            if entity_threat_levels.get(eid, ThreatLevel.NORMAL) >= HIGH_THREAT_FLOOR
        )

        total_entities = len(entity_threat_levels)
        high_threat_entities = sum(
            1 for level in entity_threat_levels.values() if level >= HIGH_THREAT_FLOOR
        )

        critical_ratio = (critical_at_risk / total_critical) if total_critical > 0 else 0.0
        network_ratio = (high_threat_entities / total_entities) if total_entities > 0 else 0.0

        should_activate = (
            critical_ratio >= CRITICAL_SERVICES_AT_RISK_RATIO
            or network_ratio >= NETWORK_WIDE_THREAT_RATIO
        )

        reason = (
            f"{critical_at_risk}/{total_critical} critical services at risk "
            f"({critical_ratio:.0%}), {high_threat_entities}/{total_entities} entities "
            f"at high threat ({network_ratio:.0%})"
        )

        return SurvivalModeAssessment(
            should_activate=should_activate,
            critical_services_at_risk=critical_at_risk,
            total_critical_services=total_critical,
            entities_in_high_threat=high_threat_entities,
            total_entities=total_entities,
            reason=reason,
        )

    def update(self, entity_threat_levels: Dict[str, ThreatLevel]) -> SurvivalModeState:
        assessment = self.assess(entity_threat_levels)

        if not self.state.is_active and assessment.should_activate:
            self._transition(True, assessment.reason)
        elif self.state.is_active and self._safe_to_deactivate(entity_threat_levels):
            self._transition(False, "conditions returned well below activation thresholds")

        return self.state

    def _safe_to_deactivate(self, entity_threat_levels: Dict[str, ThreatLevel]) -> bool:
        assessment = self.assess(entity_threat_levels)
        critical_ratio = (
            assessment.critical_services_at_risk / assessment.total_critical_services
            if assessment.total_critical_services > 0 else 0.0
        )
        network_ratio = (
            assessment.entities_in_high_threat / assessment.total_entities
            if assessment.total_entities > 0 else 0.0
        )
        return (
            critical_ratio <= CRITICAL_SERVICES_AT_RISK_RATIO * DEACTIVATION_SAFETY_MARGIN
            and network_ratio <= NETWORK_WIDE_THREAT_RATIO * DEACTIVATION_SAFETY_MARGIN
        )

    def _transition(self, activate: bool, reason: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.state.history.append(
            SurvivalModeEvent(
                timestamp=now,
                action="ACTIVATED" if activate else "DEACTIVATED",
                reason=reason,
            )
        )
        self.state.is_active = activate
        self.state.activated_at = now if activate else ""