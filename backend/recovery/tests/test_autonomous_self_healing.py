import pytest
from unittest.mock import MagicMock
from recovery.memory import NetworkMemory
from recovery.context_aware_recovery import RecoveryContext
from recovery.autonomous_self_healing import AutonomousSelfHealing
from security.threat_level_models import ThreatLevel


@pytest.fixture
def memory():
    return NetworkMemory()


@pytest.fixture
def context():
    return RecoveryContext(
        failed_nodes=["A"],
        active_services=["web", "db"],
        network_load=0.3,
        trust_levels={"A": "NORMAL"},
    )


@pytest.fixture
def healthy_state():
    return {"reachable": True, "services_up": True, "latency_ms": 50, "error_rate": 0.01}


def make_gate(allowed, requires_manual=False):
    gate = MagicMock()
    gate.check.return_value = MagicMock(
        allowed=allowed,
        requires_manual_approval=requires_manual,
        reason="test reason",
    )
    return gate


def test_successful_healing(memory, context, healthy_state):
    ash = AutonomousSelfHealing(memory)
    outcome = ash.heal("A", context, healthy_state)
    assert outcome.security_blocked is False
    assert outcome.strategy_chosen is not None
    assert outcome.recovery_success is True


def test_security_gate_blocks_healing(memory, context, healthy_state):
    ash = AutonomousSelfHealing(memory)
    gate = make_gate(allowed=False)
    outcome = ash.heal("A", context, healthy_state, ThreatLevel.QUARANTINE, gate)
    assert outcome.security_blocked is True
    assert outcome.strategy_chosen is None


def test_requires_manual_approval(memory, context, healthy_state):
    ash = AutonomousSelfHealing(memory)
    gate = make_gate(allowed=False, requires_manual=True)
    outcome = ash.heal("A", context, healthy_state, ThreatLevel.SUSPICIOUS, gate)
    assert outcome.requires_manual_approval is True


def test_failed_recovery_triggers_rollback(memory, context, healthy_state):
    ash = AutonomousSelfHealing(memory)
    def always_fails(stage, ctx):
        return False, {"error": "failed"}
    outcome = ash.heal("A", context, healthy_state, stage_executor=always_fails)
    assert outcome.rolled_back is True
    assert outcome.recovery_success is False


def test_outcome_recorded_in_history(memory, context, healthy_state):
    ash = AutonomousSelfHealing(memory)
    ash.heal("A", context, healthy_state)
    assert len(ash.history()) == 1


def test_security_allowed_proceeds(memory, context, healthy_state):
    ash = AutonomousSelfHealing(memory)
    gate = make_gate(allowed=True)
    outcome = ash.heal("A", context, healthy_state, ThreatLevel.NORMAL, gate)
    assert outcome.security_blocked is False
    assert outcome.strategy_chosen is not None
