import pytest
from recovery.models import NetworkSnapshot, RecoveryEvent
from recovery.memory import NetworkMemory


@pytest.fixture
def memory():
    return NetworkMemory()

@pytest.fixture
def sample_snapshot():
    return NetworkSnapshot(
        topology={"nodes": ["A", "B", "C"], "edges": [["A", "B"], ["B", "C"]]},
        active_services=["web", "db"],
        failed_nodes=["B"],
        metrics={"latency_ms": 120.0, "packet_loss": 0.05},
        label="pre-recovery",
    )

@pytest.fixture
def sample_event():
    return RecoveryEvent(
        trigger="node_failure",
        affected_nodes=["B"],
        strategy_used="reroute",
        success=True,
        duration_seconds=3.2,
    )

def test_save_and_retrieve_snapshot(memory, sample_snapshot):
    saved = memory.save_snapshot(sample_snapshot)
    retrieved = memory.get_snapshot(saved.snapshot_id)
    assert retrieved is not None
    assert retrieved.snapshot_id == saved.snapshot_id
    assert retrieved.failed_nodes == ["B"]

def test_latest_snapshot(memory, sample_snapshot):
    memory.save_snapshot(sample_snapshot)
    latest = memory.latest_snapshot()
    assert latest is not None
    assert latest.label == "pre-recovery"

def test_snapshots_with_failures(memory):
    healthy = NetworkSnapshot(failed_nodes=[], label="healthy")
    broken = NetworkSnapshot(failed_nodes=["X"], label="broken")
    memory.save_snapshot(healthy)
    memory.save_snapshot(broken)
    failing = memory.snapshots_with_failures()
    assert len(failing) == 1
    assert failing[0].label == "broken"

def test_record_and_retrieve_event(memory, sample_event):
    memory.record_event(sample_event)
    assert len(memory.get_events()) == 1
    assert memory.get_events()[0].strategy_used == "reroute"

def test_strategy_success_rate(memory):
    memory.record_event(RecoveryEvent(
        trigger="failure", affected_nodes=["A"],
        strategy_used="reroute", success=True, duration_seconds=1.0
    ))
    memory.record_event(RecoveryEvent(
        trigger="failure", affected_nodes=["B"],
        strategy_used="reroute", success=False, duration_seconds=5.0
    ))
    assert memory.strategy_success_rate("reroute") == 0.5
    assert memory.strategy_success_rate("restart") == 0.0

def test_summary(memory, sample_snapshot, sample_event):
    memory.save_snapshot(sample_snapshot)
    memory.record_event(sample_event)
    s = memory.summary()
    assert s["total_snapshots"] == 1
    assert s["total_events"] == 1
    assert s["successful_recoveries"] == 1

def test_max_snapshots_eviction():
    memory = NetworkMemory(max_snapshots=3)
    for i in range(4):
        memory.save_snapshot(NetworkSnapshot(label=f"snap-{i}"))
    assert len(memory.all_snapshots()) == 3
