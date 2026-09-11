import pytest

from security.policy_engine import PolicyEngine


def test_default_policies_are_loaded():
    engine = PolicyEngine()
    assert engine.get("critical_services_require_manual_approval") is True
    assert engine.get("quarantine_threat_threshold") == 4


def test_unknown_policy_raises_key_error():
    engine = PolicyEngine()
    with pytest.raises(KeyError):
        engine.get("nonexistent_policy")


def test_overrides_apply_at_construction():
    engine = PolicyEngine(overrides={"quarantine_threat_threshold": 5})
    assert engine.get("quarantine_threat_threshold") == 5


def test_set_policy_updates_value():
    engine = PolicyEngine()
    engine.set_policy("sla_default_uptime_target_percent", 99.99)
    assert engine.get("sla_default_uptime_target_percent") == 99.99


def test_evaluate_max_passes_within_limit():
    engine = PolicyEngine()
    result = engine.evaluate_max("sla_default_max_response_time_ms", 150.0)
    assert result.passed is True


def test_evaluate_max_fails_over_limit():
    engine = PolicyEngine()
    result = engine.evaluate_max("sla_default_max_response_time_ms", 500.0)
    assert result.passed is False


def test_evaluate_min_passes_above_minimum():
    engine = PolicyEngine()
    result = engine.evaluate_min("sla_default_uptime_target_percent", 99.95)
    assert result.passed is True


def test_evaluate_min_fails_below_minimum():
    engine = PolicyEngine()
    result = engine.evaluate_min("sla_default_uptime_target_percent", 90.0)
    assert result.passed is False


def test_all_policies_returns_full_dict():
    engine = PolicyEngine()
    all_policies = engine.all_policies()
    assert "trust_decay_trigger_count" in all_policies
    assert len(all_policies) == 9