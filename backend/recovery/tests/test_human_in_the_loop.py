import pytest
from recovery.human_in_the_loop import HumanInTheLoop, ApprovalStatus


@pytest.fixture
def hitl():
    return HumanInTheLoop(auto_approve_above=0.90)


def test_request_created_as_pending(hitl):
    req = hitl.request_approval("A", "reroute", "node failed", confidence=0.5)
    assert req.status == ApprovalStatus.PENDING

def test_auto_approved_when_confidence_high(hitl):
    req = hitl.request_approval("A", "reroute", "node failed", confidence=0.95)
    assert req.status == ApprovalStatus.APPROVED
    assert req.decided_by == "auto"

def test_manual_approve(hitl):
    req = hitl.request_approval("A", "reroute", "node failed", confidence=0.5)
    approved = hitl.approve(req.request_id, operator="alice")
    assert approved.status == ApprovalStatus.APPROVED
    assert approved.decided_by == "alice"

def test_manual_reject(hitl):
    req = hitl.request_approval("A", "restart", "node failed", confidence=0.3)
    rejected = hitl.reject(req.request_id, operator="bob", notes="too risky")
    assert rejected.status == ApprovalStatus.REJECTED
    assert rejected.notes == "too risky"

def test_pending_list(hitl):
    hitl.request_approval("A", "reroute", "fail", confidence=0.5)
    hitl.request_approval("B", "restart", "fail", confidence=0.5)
    assert len(hitl.pending()) == 2

def test_approved_not_in_pending(hitl):
    req = hitl.request_approval("A", "reroute", "fail", confidence=0.5)
    hitl.approve(req.request_id, "alice")
    assert len(hitl.pending()) == 0

def test_get_request(hitl):
    req = hitl.request_approval("A", "reroute", "fail", confidence=0.5)
    fetched = hitl.get(req.request_id)
    assert fetched.node_id == "A"
