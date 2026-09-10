import pytest
from recovery.ab_testing import RecoveryABTesting


@pytest.fixture
def ab():
    return RecoveryABTesting("reroute", "restart")


def test_record_run(ab):
    ab.record("reroute", "A", success=True, duration_seconds=2.0)
    assert ab.total_runs() == 1

def test_winner_by_success_rate(ab):
    ab.record("reroute", "A", True, 2.0)
    ab.record("reroute", "A", True, 2.0)
    ab.record("restart", "A", False, 5.0)
    ab.record("restart", "A", True, 5.0)
    result = ab.result()
    assert result.winner == "reroute"

def test_winner_by_speed_when_tied(ab):
    ab.record("reroute", "A", True, 2.0)
    ab.record("restart", "A", True, 8.0)
    result = ab.result()
    assert result.winner == "reroute"

def test_no_data_returns_no_winner(ab):
    result = ab.result()
    assert result.winner is None

def test_conclusion_not_empty(ab):
    ab.record("reroute", "A", True, 2.0)
    ab.record("restart", "A", False, 5.0)
    result = ab.result()
    assert len(result.conclusion) > 0

def test_success_rates_correct(ab):
    ab.record("reroute", "A", True, 2.0)
    ab.record("reroute", "A", False, 2.0)
    result = ab.result()
    assert result.success_rate_a == 0.5

def test_equivalent_strategies(ab):
    ab.record("reroute", "A", True, 3.0)
    ab.record("restart", "A", True, 3.0)
    result = ab.result()
    assert result.winner is None
