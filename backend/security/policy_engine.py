from typing import Any, Dict, Optional

from .policy_models import Policy, PolicyEvaluation

# Default policies — mirrors the thresholds already used across the
# Security track, now centralized so they can be changed in one place.
DEFAULT_POLICIES: Dict[str, Any] = {
    "critical_services_require_manual_approval": True,
    "quarantine_threat_threshold": 4,   # ThreatLevel.QUARANTINE
    "block_recovery_threat_threshold": 4,
    "safe_recovery_threat_threshold": 2,  # ThreatLevel.SUSPICIOUS
    "max_threat_downgrade_steps": 1,
    "sla_default_uptime_target_percent": 99.9,
    "sla_default_max_response_time_ms": 200.0,
    "trust_decay_trigger_count": 2,
    "trust_recovery_trigger_count": 3,
}

DEFAULT_DESCRIPTIONS: Dict[str, str] = {
    "critical_services_require_manual_approval": "Whether critical services need human sign-off before recovery",
    "quarantine_threat_threshold": "Threat level at which an entity is quarantined",
    "block_recovery_threat_threshold": "Threat level at which recovery actions are blocked entirely",
    "safe_recovery_threat_threshold": "Threat level below which recovery may proceed automatically",
    "max_threat_downgrade_steps": "How many threat levels an entity may step down per update",
    "sla_default_uptime_target_percent": "Default uptime target for services without a custom SLA",
    "sla_default_max_response_time_ms": "Default max response time for services without a custom SLA",
    "trust_decay_trigger_count": "Consecutive suspicious events before trust decay kicks in",
    "trust_recovery_trigger_count": "Consecutive normal events before trust recovery kicks in",
}


class PolicyEngine:
    """
    Central, configurable source of truth for thresholds and rules used
    across the Security track. Other modules should read their configurable
    values from here instead of hardcoding constants, so policy changes
    don't require code changes.
    """

    def __init__(self, overrides: Optional[Dict[str, Any]] = None) -> None:
        self._policies: Dict[str, Policy] = {
            key: Policy(key=key, value=value, description=DEFAULT_DESCRIPTIONS.get(key, ""))
            for key, value in DEFAULT_POLICIES.items()
        }
        if overrides:
            for key, value in overrides.items():
                self.set_policy(key, value)

    def get(self, key: str) -> Any:
        policy = self._policies.get(key)
        if policy is None:
            raise KeyError(f"No policy registered for key '{key}'")
        return policy.value

    def set_policy(self, key: str, value: Any, description: str = "") -> None:
        existing = self._policies.get(key)
        self._policies[key] = Policy(
            key=key,
            value=value,
            description=description or (existing.description if existing else ""),
        )

    def all_policies(self) -> Dict[str, Any]:
        return {key: p.value for key, p in self._policies.items()}

    def evaluate_max(self, key: str, actual_value: float) -> PolicyEvaluation:
        """Passes if actual_value is <= the policy's value (e.g. thresholds that cap something)."""
        policy_value = self.get(key)
        passed = actual_value <= policy_value
        return PolicyEvaluation(
            policy_key=key,
            passed=passed,
            policy_value=policy_value,
            actual_value=actual_value,
            reason=f"{actual_value} {'<=' if passed else '>'} policy limit {policy_value} for '{key}'",
        )

    def evaluate_min(self, key: str, actual_value: float) -> PolicyEvaluation:
        """Passes if actual_value is >= the policy's value (e.g. minimum uptime targets)."""
        policy_value = self.get(key)
        passed = actual_value >= policy_value
        return PolicyEvaluation(
            policy_key=key,
            passed=passed,
            policy_value=policy_value,
            actual_value=actual_value,
            reason=f"{actual_value} {'>=' if passed else '<'} policy minimum {policy_value} for '{key}'",
        )