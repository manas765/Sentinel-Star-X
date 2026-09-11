import pytest
from recovery.resource_orchestrator import ResourceAwareOrchestrator, ResourceSnapshot


@pytest.fixture
def orch():
    return ResourceAwareOrchestrator()


@pytest.fixture
def rich_resources():
    return ResourceSnapshot(cpu_available=0.8, memory_available=0.8, bandwidth_available=0.8)


@pytest.fixture
def poor_resources():
    return ResourceSnapshot(cpu_available=0.05, memory_available=0.05, bandwidth_available=0.05)


def test_approved_with_enough_resources(orch, rich_resources):
    decision = orch.orchestrate("A", "reroute", rich_resources)
    assert decision.approved is True
    assert decision.queued is False


def test_denied_with_poor_resources(orch, poor_resources):
    decision = orch.orchestrate("A", "restart", poor_resources)
    assert decision.approved is False
    assert decision.queued is True


def test_queued_jobs_stored(orch, poor_resources):
    orch.orchestrate("A", "restart", poor_resources)
    assert len(orch.queue()) == 1


def test_flush_queue_approves_when_resources_free(orch, poor_resources, rich_resources):
    orch.orchestrate("A", "restart", poor_resources)
    approved = orch.flush_queue(rich_resources)
    assert len(approved) == 1
    assert approved[0].approved is True
    assert len(orch.queue()) == 0


def test_too_many_jobs_queues(orch):
    busy = ResourceSnapshot(cpu_available=0.9, memory_available=0.9, bandwidth_available=0.9, active_recovery_jobs=3)
    decision = orch.orchestrate("A", "reroute", busy)
    assert decision.approved is False


def test_unknown_strategy_denied(orch, rich_resources):
    ok, reason = orch.can_run("unknown_strategy", rich_resources)
    assert ok is False


def test_history_recorded(orch, rich_resources):
    orch.orchestrate("A", "reroute", rich_resources)
    orch.orchestrate("B", "restart", rich_resources)
    assert len(orch.history()) == 2
