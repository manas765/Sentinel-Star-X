from datetime import datetime, timedelta, timezone

from security.event_correlator import EventCorrelator
from security.event_correlation_models import SecurityEvent


def _ts(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def test_low_risk_events_are_ignored():
    correlator = EventCorrelator()
    events = [SecurityEvent(entity_id="PC-1", timestamp=_ts(), risk_score=0.1)]
    incidents = correlator.correlate(events)
    assert incidents == []


def test_single_unrelated_event_becomes_isolated_incident():
    correlator = EventCorrelator()
    events = [SecurityEvent(entity_id="PC-1", timestamp=_ts(), risk_score=0.5)]
    incidents = correlator.correlate(events)
    assert len(incidents) == 1
    assert incidents[0].event_count == 1
    assert "isolated" in incidents[0].correlation_reason


def test_events_with_shared_peer_are_fused():
    correlator = EventCorrelator()
    events = [
        SecurityEvent(entity_id="PC-1", timestamp=_ts(0), risk_score=0.5, related_peers=["PC-2"]),
        SecurityEvent(entity_id="PC-2", timestamp=_ts(500), risk_score=0.6, related_peers=["PC-1"]),
    ]
    incidents = correlator.correlate(events)
    assert len(incidents) == 1
    assert set(incidents[0].entity_ids) == {"PC-1", "PC-2"}


def test_events_close_in_time_are_fused_even_without_shared_peer():
    correlator = EventCorrelator()
    events = [
        SecurityEvent(entity_id="PC-3", timestamp=_ts(0), risk_score=0.4),
        SecurityEvent(entity_id="PC-4", timestamp=_ts(20), risk_score=0.4),
    ]
    incidents = correlator.correlate(events)
    assert len(incidents) == 1
    assert incidents[0].event_count == 2


def test_events_far_apart_in_time_with_no_shared_peer_stay_separate():
    correlator = EventCorrelator()
    events = [
        SecurityEvent(entity_id="PC-5", timestamp=_ts(0), risk_score=0.4),
        SecurityEvent(entity_id="PC-6", timestamp=_ts(600), risk_score=0.4),
    ]
    incidents = correlator.correlate(events)
    assert len(incidents) == 2


def test_combined_risk_score_increases_with_more_correlated_events():
    correlator = EventCorrelator()
    events = [
        SecurityEvent(entity_id="PC-7", timestamp=_ts(0), risk_score=0.5, related_peers=["PC-8", "PC-9"]),
        SecurityEvent(entity_id="PC-8", timestamp=_ts(5), risk_score=0.5, related_peers=["PC-7"]),
        SecurityEvent(entity_id="PC-9", timestamp=_ts(10), risk_score=0.5, related_peers=["PC-7"]),
    ]
    incidents = correlator.correlate(events)
    assert len(incidents) == 1
    assert incidents[0].combined_risk_score > 0.5