from security.audit_trail import AuditTrail


def test_record_creates_unique_ids():
    trail = AuditTrail()
    e1 = trail.record("TrustEngine", "PC-1", "trust_updated")
    e2 = trail.record("TrustEngine", "PC-1", "trust_updated")
    assert e1.entry_id != e2.entry_id


def test_entries_are_never_removed_only_appended():
    trail = AuditTrail()
    trail.record("TrustEngine", "PC-1", "trust_updated")
    trail.record("ThreatLevelManager", "PC-1", "threat_escalated")
    assert len(trail.all_entries()) == 2


def test_for_entity_filters_correctly():
    trail = AuditTrail()
    trail.record("TrustEngine", "PC-1", "trust_updated")
    trail.record("TrustEngine", "PC-2", "trust_updated")
    entries = trail.for_entity("PC-1")
    assert len(entries) == 1
    assert entries[0].entity_id == "PC-1"


def test_for_module_filters_correctly():
    trail = AuditTrail()
    trail.record("TrustEngine", "PC-1", "trust_updated")
    trail.record("SurvivalModeManager", "PC-1", "survival_mode_activated")
    entries = trail.for_module("SurvivalModeManager")
    assert len(entries) == 1
    assert entries[0].source_module == "SurvivalModeManager"


def test_for_event_type_filters_correctly():
    trail = AuditTrail()
    trail.record("ThreatLevelManager", "PC-1", "threat_escalated", details={"to": "RESTRICT"})
    trail.record("ThreatLevelManager", "PC-1", "threat_deescalated", details={"to": "SUSPICIOUS"})
    entries = trail.for_event_type("threat_escalated")
    assert len(entries) == 1


def test_reconstruct_timeline_includes_all_entries_for_entity():
    trail = AuditTrail()
    trail.record("TrustEngine", "PC-1", "trust_updated", details={"delta": -5})
    trail.record("ThreatLevelManager", "PC-1", "threat_escalated", details={"to": "RESTRICT"})
    timeline = trail.reconstruct_timeline("PC-1")
    assert "TrustEngine" in timeline
    assert "ThreatLevelManager" in timeline
    assert "delta=-5" in timeline


def test_reconstruct_timeline_handles_unknown_entity():
    trail = AuditTrail()
    timeline = trail.reconstruct_timeline("GHOST")
    assert "No audit entries found" in timeline