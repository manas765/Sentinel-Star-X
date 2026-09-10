import pytest
from recovery.safe_rollback import SafeRollback


@pytest.fixture
def rb():
    return SafeRollback()

def test_save_and_has_snapshot(rb):
    rb.save("A", {"status": "healthy"})
    assert rb.has_snapshot("A") is True

def test_rollback_success(rb):
    rb.save("A", {"status": "healthy"})
    result = rb.rollback("A", reason="verification_failed")
    assert result.success is True
    assert result.node_id == "A"

def test_rollback_no_snapshot(rb):
    result = rb.rollback("Z")
    assert result.success is False
    assert "No snapshot" in result.reason

def test_get_snapshot_returns_state(rb):
    rb.save("A", {"status": "healthy", "load": 0.3})
    snap = rb.get_snapshot("A")
    assert snap.state["load"] == 0.3

def test_clear_removes_snapshot(rb):
    rb.save("A", {"status": "healthy"})
    rb.clear("A")
    assert rb.has_snapshot("A") is False

def test_rollback_reason_recorded(rb):
    rb.save("A", {"status": "healthy"})
    result = rb.rollback("A", reason="auto_triggered")
    assert result.reason == "auto_triggered"
