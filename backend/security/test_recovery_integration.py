from security.recovery_integration import (
    enforce_security_gate,
    get_shared_threat_manager,
)
from security.threat_level_models import ThreatLevel


def test_normal_node_is_allowed_to_recover():
    decision = enforce_security_gate("PC-100")
    assert decision.allowed is True


def test_node_under_high_threat_is_blocked_from_recovery():
    threat_manager = get_shared_threat_manager()
    threat_manager.update("PC-101", risk_score=0.9)  # escalates to EMERGENCY
    decision = enforce_security_gate("PC-101")
    assert decision.allowed is False
    assert decision.recommended_action == "BLOCK"