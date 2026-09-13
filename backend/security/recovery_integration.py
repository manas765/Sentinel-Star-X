"""
Integration point between the Security track and the Recovery track.
Aakash's MultiObjectiveDecisionEngine.decide() should call
enforce_security_gate() at the very start, before simulating or
scoring any recovery strategy, and respect the returned decision.
"""

from typing import Optional

from .critical_service_protection import CriticalServiceProtection
from .recovery_gate_models import RecoveryGateDecision
from .security_gated_recovery import SecurityGatedRecovery
from .threat_level_manager import ThreatLevelManager
from .threat_level_models import ThreatLevel

# Shared instances — in a real deployed system these would be dependency-injected,
# but for now a module-level singleton keeps the integration simple for both tracks.
_critical_protection = CriticalServiceProtection()
_threat_manager = ThreatLevelManager()
_gate = SecurityGatedRecovery(_critical_protection)


def get_shared_threat_manager() -> ThreatLevelManager:
    """Recovery track can use this if it needs to read/update threat levels directly."""
    return _threat_manager


def get_shared_critical_service_protection() -> CriticalServiceProtection:
    """Recovery track can use this to check/register critical services consistently."""
    return _critical_protection


def enforce_security_gate(node_id: str) -> RecoveryGateDecision:
    """
    Call this before executing ANY recovery action on node_id.
    Returns a RecoveryGateDecision — check `.allowed` before proceeding.
    If `.allowed` is False, do not run the recovery strategy; surface
    `.reason` and `.recommended_action` to the caller/dashboard instead.
    """
    threat_state = _threat_manager.get_state(node_id)
    return _gate.check(node_id, threat_state.level)