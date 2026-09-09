import pytest
from recovery.cost_estimator import CostFactors, RecoveryCostEstimator


@pytest.fixture
def estimator():
    return RecoveryCostEstimator()


@pytest.fixture
def reroute_factors():
    return CostFactors(
        strategy="reroute",
        affected_nodes=["A"],
        estimated_duration_seconds=4.0,
        service_downtime_seconds=2.0,
        risk_of_failure=0.1,
        manual_intervention_required=False,
        rollback_available=True,
    )


@pytest.fixture
def restart_factors():
    return CostFactors(
        strategy="restart",
        affected_nodes=["A"],
        estimated_duration_seconds=20.0,
        service_downtime_seconds=15.0,
        risk_of_failure=0.4,
        manual_intervention_required=True,
        rollback_available=False,
    )


def test_estimate_returns_correct_strategy(estimator, reroute_factors):
    est = estimator.estimate(reroute_factors)
    assert est.strategy == "reroute"

def test_rollback_reduces_cost(estimator, reroute_factors):
    with_rollback = estimator.estimate(reroute_factors)
    reroute_factors.rollback_available = False
    without_rollback = estimator.estimate(reroute_factors)
    assert with_rollback.total_cost < without_rollback.total_cost

def test_manual_intervention_increases_cost(estimator, reroute_factors):
    without_manual = estimator.estimate(reroute_factors)
    reroute_factors.manual_intervention_required = True
    with_manual = estimator.estimate(reroute_factors)
    assert with_manual.total_cost > without_manual.total_cost

def test_total_cost_never_negative(estimator):
    cheap = CostFactors(
        strategy="reroute",
        affected_nodes=["A"],
        estimated_duration_seconds=0.1,
        service_downtime_seconds=0.1,
        risk_of_failure=0.0,
        rollback_available=True,
    )
    est = estimator.estimate(cheap)
    assert est.total_cost >= 0.0

def test_compare_sorts_cheapest_first(estimator, reroute_factors, restart_factors):
    ranked = estimator.compare([restart_factors, reroute_factors])
    assert ranked[0].strategy == "reroute"

def test_cheapest_returns_best(estimator, reroute_factors, restart_factors):
    best = estimator.cheapest([restart_factors, reroute_factors])
    assert best is not None
    assert best.strategy == "reroute"

def test_recommendation_score_between_0_and_100(estimator, restart_factors):
    est = estimator.estimate(restart_factors)
    assert 0.0 <= est.recommendation_score <= 100.0

def test_empty_options_returns_none(estimator):
    assert estimator.cheapest([]) is None
