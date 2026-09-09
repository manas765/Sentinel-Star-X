import pytest
from recovery.models import RecoveryEvent, NetworkSnapshot
from recovery.memory import NetworkMemory
from recovery.knowledge_base import RecoveryKnowledgeBase


@pytest.fixture
def memory_with_history():
    mem = NetworkMemory()
    events = [
        RecoveryEvent(trigger="failure", affected_nodes=["A"], strategy_used="reroute", success=True, duration_seconds=2.0),
        RecoveryEvent(trigger="failure", affected_nodes=["A"], strategy_used="reroute", success=True, duration_seconds=3.0),
        RecoveryEvent(trigger="failure", affected_nodes=["A"], strategy_used="restart", success=False, duration_seconds=10.0),
        RecoveryEvent(trigger="failure", affected_nodes=["A"], strategy_used="failover", success=True, duration_seconds=8.0),
        RecoveryEvent(trigger="failure", affected_nodes=["B"], strategy_used="restart", success=True, duration_seconds=4.0),
    ]
    for e in events:
        mem.record_event(e)
    return mem


@pytest.fixture
def kb(memory_with_history):
    return RecoveryKnowledgeBase(memory_with_history)


def test_best_strategy_for_node(kb):
    assert kb.best_strategy_for_node("A") == "reroute"

def test_best_strategy_unknown_node(kb):
    assert kb.best_strategy_for_node("Z") is None

def test_fastest_successful_strategy(kb):
    assert kb.fastest_successful_strategy("A") == "reroute"

def test_fastest_strategy_unknown_node(kb):
    assert kb.fastest_successful_strategy("Z") is None

def test_known_strategies(kb):
    strategies = kb.known_strategies()
    assert set(strategies) == {"reroute", "restart", "failover"}

def test_strategy_summary_order(kb):
    summary = kb.strategy_summary()
    assert summary[0]["strategy"] == "reroute"
    assert summary[0]["success_rate"] == 1.0

def test_recommend(kb):
    rec = kb.recommend("A")
    assert rec["has_history"] is True
    assert rec["recommended_strategy"] == "reroute"
    assert rec["node_id"] == "A"

def test_recommend_no_history(kb):
    rec = kb.recommend("Z")
    assert rec["has_history"] is False
    assert rec["recommended_strategy"] is None
