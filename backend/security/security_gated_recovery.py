from .critical_service_protection import CriticalServiceProtection
from .recovery_gate_models import RecoveryGateDecision
from .threat_level_models import ThreatLevel

# Below this level, recovery is safe to proceed automatically.
SAFE_TO_RECOVER_THRESHOLD = ThreatLevel.SUSPICIOUS

# At or above this level, recovery is blocked entirely — the entity is
# likely still actively compromised, so "fixing" it would just hand
# control back to whatever is attacking it.
BLOCK_RECOVERY_THRESHOLD = ThreatLevel.QUARANTINE


class SecurityGatedRecovery:
    """
    Checkpoint that the Recovery track must consult before executing any
    automated recovery/self-healing action. Prevents recovery from
    "fixing" a node that may still be under active attack.
    """

    def __init__(self, critical_service_protection: CriticalServiceProtection) -> None:
        self.critical_service_protection = critical_service_protection

    def check(self, entity_id: str, threat_level: ThreatLevel) -> RecoveryGateDecision:
        is_critical = self.critical_service_protection.is_critical(entity_id)

        if threat_level >= BLOCK_RECOVERY_THRESHOLD:
            return RecoveryGateDecision(
                entity_id=entity_id,
                allowed=False,
                requires_manual_approval=False,
                reason=(
                    f"threat level {threat_level.name} indicates the entity may still be "
                    "actively compromised; recovery blocked until it is contained"
                ),
                recommended_action="BLOCK",
            )

        if threat_level >= SAFE_TO_RECOVER_THRESHOLD:
            # Between SUSPICIOUS and QUARANTINE: critical services need a human
            # to sign off, non-critical entities can wait and be re-checked.
            if is_critical:
                return RecoveryGateDecision(
                    entity_id=entity_id,
                    allowed=False,
                    requires_manual_approval=True,
                    reason=(
                        f"critical service at threat level {threat_level.name}; "
                        "recovery requires manual approval before proceeding"
                    ),
                    recommended_action="MANUAL_APPROVAL_REQUIRED",
                )
            return RecoveryGateDecision(
                entity_id=entity_id,
                allowed=False,
                requires_manual_approval=False,
                reason=f"threat level {threat_level.name} not yet resolved; holding recovery and re-checking",
                recommended_action="HOLD_AND_MONITOR",
            )

        return RecoveryGateDecision(
            entity_id=entity_id,
            allowed=True,
            requires_manual_approval=False,
            reason=f"threat level {threat_level.name} is within safe range; recovery may proceed",
            recommended_action="PROCEED",
        )