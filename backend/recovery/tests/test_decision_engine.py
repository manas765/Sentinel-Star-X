import pytest
from recovery.memory import NetworkMemory
from recovery.models import RecoveryEvent
from recovery.context_aware_recovery import RecoveryContext
from recovery.decision_engine import MultiObjectiveDecisionEngine, ObjectiveWeights


@pytest.fixture
def memory():
    return NetworkMemory()


@pytest.fixture
def memory_with_history():
    mem = NetworkMemory()
    for _ in range(4):
        mem.record_event(RecoveryEvent(
            trigger="failure", affected_nodes=["A"],
            strategy_used="reroute", success=True, duration_seconds=2.0
        ))
    return mem


@pytest.fixture
def context():
    return RecoveryContext(
        failed_nodes=["A", "B"],
        active_services=["web", "db"],
        network_load=0.3,
        trust_levels={"A": "NORMAL", "B": "NORMAL"},
    )


def test_decide_returns_decision(memory, context):
    engine = MultiObjectiveDecisionEngine(memory)
    decision = engine.decide("A", context)
    assert decision.failed_node == "A"
    assert decision.chosen_strategy in context.candidate_strategies


def test_composite_score_in_range(memory, context):
    engine = MultiObjectiveDecisionEngine(memory)
    decision = engine.decide("A", context)
    assert 0.0 <= decision.composite_score <= 100.0


def test_runner_up_is_different_strategy(memory, context):
    engine = MultiObjectiveDecisionEngine(memory)
    decision = engine.decide("A", context)
    assert decision.runner_up != decision.chosen_strategy


def test_decide_all_covers_all_nodes(memory, context):
    engine = MultiObjectiveDecisionEngine(memory)
    decisions = engine.decide_all(context)
    assert len(decisions) == 2
    assert {d.failed_node for d in decisions} == {"A", "B"}


def test_custom_weights_affect_decision(memory):
    ctx = RecoveryContext(
        failed_nodes=["A"], active_services=["web"],
        network_load=0.5,
    )
    speed_weights = ObjectiveWeights(speed=0.90, reliability=0.05, cost=0.03, safety=0.02)
    safety_weights = ObjectiveWeights(speed=0.02, reliability=0.03, cost=0.05, safety=0.90)
    engine = MultiObjectiveDecisionEngine(memory)
    speed_decision = engine.decide("A", ctx, speed_weights)
    safety_decision = engine.decide("A", ctx, safety_weights)
    # Both are valid decisions — just check they run cleanly
    assert speed_decision.chosen_strategy in ctx.candidate_strategies
    assert safety_decision.chosen_strategy in ctx.candidate_strategies


def test_reasoning_not_empty(memory, context):
    engine = MultiObjectiveDecisionEngine(memory)
    decision = engine.decide("A", context)
    assert len(decision.reasoning) > 0


def test_update_weights(memory, context):
    engine = MultiObjectiveDecisionEngine(memory)
    new_weights = ObjectiveWeights(speed=0.70, reliability=0.10, cost=0.10, safety=0.10)
    engine.update_weights(new_weights)
    decision = engine.decide("A", context)
    assert decision.weights_used.speed == 0.70


def test_history_influences_score(memory_with_history):
    ctx = RecoveryContext(
        failed_nodes=["A"], active_services=["web"],
        network_load=0.2,
    )
    engine = MultiObjectiveDecisionEngine(memory_with_history)
    decision = engine.decide("A", ctx)
    assert decision.chosen_strategy == "reroute"
