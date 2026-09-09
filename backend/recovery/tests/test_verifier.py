import pytest
from recovery.verifier import RecoveryVerifier


@pytest.fixture
def verifier():
    return RecoveryVerifier()

def healthy_state():
    return {"reachable": True, "services_up": True, "latency_ms": 50, "error_rate": 0.01}

def test_all_checks_pass(verifier):
    result = verifier.verify("A", healthy_state())
    assert result.success is True
    assert result.confidence == 1.0

def test_unreachable_node_fails(verifier):
    state = healthy_state()
    state["reachable"] = False
    result = verifier.verify("A", state)
    assert result.success is False
    assert "node_reachable" in result.checks_failed

def test_high_latency_fails(verifier):
    state = healthy_state()
    state["latency_ms"] = 500
    result = verifier.verify("A", state)
    assert "latency_acceptable" in result.checks_failed

def test_high_error_rate_fails(verifier):
    state = healthy_state()
    state["error_rate"] = 0.20
    result = verifier.verify("A", state)
    assert "error_rate_normal" in result.checks_failed

def test_partial_failure_gives_partial_confidence(verifier):
    state = healthy_state()
    state["services_up"] = False
    result = verifier.verify("A", state)
    assert 0.0 < result.confidence < 1.0
    assert result.success is False
