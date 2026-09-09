import pytest
from recovery.memory import NetworkMemory
from recovery.models import RecoveryEvent
from recovery.context_aware_recovery import RecoveryContext
from recovery.strategy_simulator import RecoveryStrategySimulator


@pytest.fixture
def memory():
    return NetworkMemory()


@pytest.fixture
def memory_with_history():
    mem = NetworkMemory()
    for _ in range(5):
        mem.record_event(RecoveryEvent(
            trigger="failure", affected_nodes=["A"],
            strategy_used="reroute", success=True, duration_seconds=2.0
        ))
    return mem


@pytest.fixture
def context():
    return RecoveryContext(
        failed_nodes=["A"],
        active_services=["web", "db"],
        network_load=0.3,
        trust_levels={"A": "NORMAL"},
    )


def test_simulate_returns_result(memory, context):
    sim = RecoveryStrategySimulator(memory)
    result = sim.simulate("A", "reroute", context)
    assert result.strategy == "reroute"
    assert 0.0 <= result.projected_success_probability <= 1.0


def test_simulate_all_returns_all_strategies(memory, context):
    sim = RecoveryStrategySimulator(memory)
    results = sim.simulate_all_strategies("A", context)
    strategies = {r.strategy for r in results}
    assert strategies == set(context.candidate_strategies)


def test_results_sorted_by_probability(memory, context):
    sim = RecoveryStrategySimulator(memory)
    results = sim.simulate_all_strategies("A", context)
    probs = [r.projected_success_probability for r in results]
    assert probs == sorted(probs, reverse=True)


def test_untrusted_node_gets_warning(memory):
    sim = RecoveryStrategySimulator(memory)
    ctx = RecoveryContext(
        failed_nodes=["X"], active_services=[], network_load=0.2,
        trust_levels={"X": "UNTRUSTED"}
    )
    result = sim.simulate("X", "reroute", ctx)
    assert any("UNTRUSTED" in w for w in result.warnings)


def test_high_load_generates_warning(memory):
    sim = RecoveryStrategySimulator(memory)
    ctx = RecoveryContext(
        failed_nodes=["A"], active_services=[], network_load=0.9,
    )
    result = sim.simulate("A", "reroute", ctx)
    assert any("high" in w.lower() for w in result.warnings)


def test_history_boosts_probability(memory_with_history, context):
    sim_with = RecoveryStrategySimulator(memory_with_history)
    sim_without = RecoveryStrategySimulator(NetworkMemory())
    with_hist = sim_with.simulate("A", "reroute", context)
    without_hist = sim_without.simulate("A", "reroute", context)
    assert with_hist.projected_success_probability >= without_hist.projected_success_probability


def test_best_simulation_returns_highest_prob(memory, context):
    sim = RecoveryStrategySimulator(memory)
    best = sim.best_simulation("A", context)
    all_results = sim.simulate_all_strategies("A", context)
    assert best.projected_success_probability == max(r.projected_success_probability for r in all_results)


def test_simulation_history_recorded(memory, context):
    sim = RecoveryStrategySimulator(memory)
    sim.simulate("A", "reroute", context)
    sim.simulate("A", "restart", context)
    assert len(sim.simulation_history()) == 2
