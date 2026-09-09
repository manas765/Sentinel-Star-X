import pytest
from recovery.memory import NetworkMemory
from recovery.models import RecoveryEvent
from recovery.context_aware_recovery import ContextAwareRecovery, RecoveryContext


@pytest.fixture
def empty_memory():
    return NetworkMemory()


@pytest.fixture
def memory_with_history():
    mem = NetworkMemory()
    for _ in range(3):
        mem.record_event(RecoveryEvent(
            trigger="failure", affected_nodes=["A"],
            strategy_used="reroute", success=True, duration_seconds=2.0
        ))
    return mem


@pytest.fixture
def basic_context():
    return RecoveryContext(
        failed_nodes=["A"],
        active_services=["web", "db"],
        network_load=0.3,
        trust_levels={"A": "NORMAL"},
    )


def test_returns_decision_for_node(empty_memory, basic_context):
    car = ContextAwareRecovery(empty_memory)
    decision = car.decide("A", basic_context)
    assert decision.failed_node == "A"
    assert decision.chosen_strategy in basic_context.candidate_strategies


def test_trust_blocked_node_gets_isolated(empty_memory):
    car = ContextAwareRecovery(empty_memory)
    ctx = RecoveryContext(
        failed_nodes=["X"],
        active_services=["web"],
        network_load=0.2,
        trust_levels={"X": "UNTRUSTED"},
    )
    decision = car.decide("X", ctx)
    assert decision.trust_blocked is True
    assert decision.chosen_strategy == "isolate"


def test_history_influences_decision(memory_with_history, basic_context):
    car = ContextAwareRecovery(memory_with_history)
    decision = car.decide("A", basic_context)
    assert decision.history_based is True
    assert decision.chosen_strategy == "reroute"


def test_no_history_still_returns_decision(empty_memory, basic_context):
    car = ContextAwareRecovery(empty_memory)
    decision = car.decide("A", basic_context)
    assert decision.chosen_strategy is not None
    assert decision.history_based is False


def test_high_load_increases_cost(empty_memory):
    car = ContextAwareRecovery(empty_memory)
    low_load = RecoveryContext(
        failed_nodes=["A"],
        active_services=["web", "db", "auth"],
        network_load=0.1,
        trust_levels={"A": "SUSPICIOUS"},   # manual=True so costs are real
    )
    high_load = RecoveryContext(
        failed_nodes=["A"],
        active_services=["web", "db", "auth"],
        network_load=0.9,
        trust_levels={"A": "SUSPICIOUS"},
    )
    low_decision = car.decide("A", low_load)
    high_decision = car.decide("A", high_load)
    assert high_decision.estimated_cost.total_cost > low_decision.estimated_cost.total_cost


def test_decide_all_handles_multiple_nodes(empty_memory):
    car = ContextAwareRecovery(empty_memory)
    ctx = RecoveryContext(
        failed_nodes=["A", "B", "C"],
        active_services=["web"],
        network_load=0.5,
    )
    decisions = car.decide_all(ctx)
    assert len(decisions) == 3
    assert {d.failed_node for d in decisions} == {"A", "B", "C"}


def test_reasoning_is_not_empty(empty_memory, basic_context):
    car = ContextAwareRecovery(empty_memory)
    decision = car.decide("A", basic_context)
    assert len(decision.reasoning) > 0
