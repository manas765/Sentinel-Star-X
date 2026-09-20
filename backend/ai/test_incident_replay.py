"""
backend/ai/test_incident_replay.py
Run with: pytest backend/ai/test_incident_replay.py -v
"""

from backend.ai.anomaly_detection import detect_anomalies, detect_link_anomalies
from backend.ai.explainable_ai import explain_network_state
from backend.ai.failure_classification import classify_failures, classify_link_failures
from backend.ai.incident_replay import IncidentReplayBuffer
from backend.ai.root_cause_analysis import analyze_root_causes
from backend.ai.telemetry_sim import AnomalyType, SyntheticTelemetryGenerator


def _record_tick(buffer, gen, snap):
    node_anomalies = detect_anomalies(snap, central_node_id=gen.central_node_id)
    link_anomalies = detect_link_anomalies(snap)
    classifications = classify_failures(node_anomalies)
    link_classifications = classify_link_failures(link_anomalies)
    root_causes = analyze_root_causes(node_anomalies, link_anomalies, gen.topology, gen.central_node_id)
    explanations = explain_network_state(node_anomalies, link_anomalies, gen.topology, gen.central_node_id)
    buffer.record(
        timestamp=snap.timestamp,
        node_anomalies=node_anomalies,
        link_anomalies=link_anomalies,
        classifications=classifications,
        link_classifications=link_classifications,
        root_causes=root_causes,
        explanations=explanations,
    )


def test_no_incident_recorded_when_all_healthy():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=1)
    buffer = IncidentReplayBuffer()
    for snap in gen.stream(ticks=5):
        _record_tick(buffer, gen, snap)
    assert buffer.list_incidents() == []


def test_incident_created_and_closed_around_anomaly_window():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=2)
    buffer = IncidentReplayBuffer()
    for i, snap in enumerate(
        gen.stream(ticks=9, anomaly_at=3, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-0")
    ):
        if i == 6:
            break
        _record_tick(buffer, gen, snap)
    for _ in range(3):
        _record_tick(buffer, gen, gen.generate_snapshot())

    incidents = buffer.list_incidents()
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident["start_tick"] == 3
    assert incident["end_tick"] == 5
    assert incident["peak_severity"] == "critical"
    assert "leaf-0" in incident["root_cause_ids"]


def test_replay_returns_ticks_within_incident_bounds():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=3)
    buffer = IncidentReplayBuffer()
    for i, snap in enumerate(
        gen.stream(ticks=6, anomaly_at=2, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-1")
    ):
        if i == 5:
            break
        _record_tick(buffer, gen, snap)
    for _ in range(2):
        _record_tick(buffer, gen, gen.generate_snapshot())

    incidents = buffer.list_incidents()
    incident_id = incidents[0]["incident_id"]
    ticks = buffer.replay(incident_id)
    assert len(ticks) == incidents[0]["tick_count"]
    assert all(t["has_anomaly"] for t in ticks)
    tick_indices = [t["tick_index"] for t in ticks]
    assert tick_indices == sorted(tick_indices)


def test_ongoing_incident_has_no_end_tick_and_is_still_listed():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=4)
    buffer = IncidentReplayBuffer()
    for snap in gen.stream(ticks=4, anomaly_at=1, anomaly=AnomalyType.NODE_DOWN, anomaly_target="leaf-2"):
        _record_tick(buffer, gen, snap)

    incidents = buffer.list_incidents()
    assert len(incidents) == 1
    assert incidents[0]["end_tick"] is None
    replay = buffer.replay(incidents[0]["incident_id"])
    assert len(replay) == 3


def test_replay_unknown_incident_returns_empty():
    buffer = IncidentReplayBuffer()
    assert buffer.replay(999) == []


def test_buffer_trims_to_max_ticks():
    gen = SyntheticTelemetryGenerator(num_leaves=2, seed=5)
    buffer = IncidentReplayBuffer(max_ticks=3)
    for _ in range(10):
        _record_tick(buffer, gen, gen.generate_snapshot())
    assert len(buffer._ticks) == 3
    assert buffer._ticks[-1].tick_index == 9


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")