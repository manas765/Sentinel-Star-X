from security.security_gated_recovery import SecurityGatedRecovery
from security.critical_service_protection import CriticalServiceProtection
from security.critical_service_models import CriticalService
from security.threat_level_models import ThreatLevel


def test_normal_threat_allows_recovery():
    protection = CriticalServiceProtection()
    gate = SecurityGatedRecovery(protection)
    decision = gate.check("PC-50", ThreatLevel.NORMAL)
    assert decision.allowed is True
    assert decision.recommended_action == "PROCEED"


def test_quarantine_blocks_recovery():
    protection = CriticalServiceProtection()
    gate = SecurityGatedRecovery(protection)
    decision = gate.check("PC-51", ThreatLevel.QUARANTINE)
    assert decision.allowed is False
    assert decision.recommended_action == "BLOCK"


def test_emergency_blocks_recovery():
    protection = CriticalServiceProtection()
    gate = SecurityGatedRecovery(protection)
    decision = gate.check("PC-52", ThreatLevel.EMERGENCY)
    assert decision.allowed is False
    assert decision.recommended_action == "BLOCK"


def test_suspicious_non_critical_holds_and_monitors():
    protection = CriticalServiceProtection()
    gate = SecurityGatedRecovery(protection)
    decision = gate.check("PC-53", ThreatLevel.SUSPICIOUS)
    assert decision.allowed is False
    assert decision.requires_manual_approval is False
    assert decision.recommended_action == "HOLD_AND_MONITOR"


def test_suspicious_critical_service_requires_manual_approval():
    protection = CriticalServiceProtection()
    protection.register_critical_service(
        CriticalService(entity_id="DB-01", name="Primary Database")
    )
    gate = SecurityGatedRecovery(protection)
    decision = gate.check("DB-01", ThreatLevel.SUSPICIOUS)
    assert decision.allowed is False
    assert decision.requires_manual_approval is True
    assert decision.recommended_action == "MANUAL_APPROVAL_REQUIRED"


def test_restrict_level_non_critical_still_holds():
    protection = CriticalServiceProtection()
    gate = SecurityGatedRecovery(protection)
    decision = gate.check("PC-54", ThreatLevel.RESTRICT)
    assert decision.allowed is False
    assert decision.recommended_action == "HOLD_AND_MONITOR"