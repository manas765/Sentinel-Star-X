from typing import Dict, List, Optional

from .critical_service_models import CriticalService, ProtectionStatus
from .threat_level_models import ThreatLevel

# Critical services escalate to "requires immediate action" sooner than
# normal entities, since their impact radius is much larger.
CRITICAL_ACTION_THRESHOLD = ThreatLevel.SUSPICIOUS  # normal entities wait until RESTRICT
NORMAL_ACTION_THRESHOLD = ThreatLevel.RESTRICT


class CriticalServiceProtection:
    """
    Tracks which entities are critical services and applies stricter
    protection rules to them than to ordinary network entities.
    """

    def __init__(self) -> None:
        self._services: Dict[str, CriticalService] = {}

    def register_critical_service(self, service: CriticalService) -> None:
        self._services[service.entity_id] = service

    def is_critical(self, entity_id: str) -> bool:
        return entity_id in self._services

    def get_service(self, entity_id: str) -> Optional[CriticalService]:
        return self._services.get(entity_id)

    def all_critical_ids(self) -> List[str]:
        return list(self._services.keys())

    def assess_protection(self, entity_id: str, current_threat_level: ThreatLevel) -> ProtectionStatus:
        service = self._services.get(entity_id)
        is_critical = service is not None
        threshold = CRITICAL_ACTION_THRESHOLD if is_critical else NORMAL_ACTION_THRESHOLD
        requires_action = current_threat_level >= threshold

        if is_critical and requires_action:
            reason = (
                f"critical service '{service.name}' at threat level "
                f"{current_threat_level.name}, exceeds critical threshold {threshold.name}"
            )
        elif is_critical:
            reason = (
                f"critical service '{service.name}' at threat level "
                f"{current_threat_level.name}, within acceptable range"
            )
        elif requires_action:
            reason = f"standard entity at threat level {current_threat_level.name}, exceeds threshold {threshold.name}"
        else:
            reason = f"standard entity at threat level {current_threat_level.name}, within acceptable range"

        return ProtectionStatus(
            entity_id=entity_id,
            is_critical=is_critical,
            priority=service.priority if service else 999,
            effective_threat_level=current_threat_level.name,
            requires_immediate_action=requires_action,
            reason=reason,
        )

    def get_dependent_impact(self, entity_id: str) -> List[str]:
        """
        Returns all critical services that depend on this entity —
        useful for understanding blast radius if it goes down.
        """
        impacted = []
        for service in self._services.values():
            if entity_id in service.dependent_services:
                impacted.append(service.entity_id)
        return impacted