from trust.trust_engine import TrustEngine


def test_new_entity_starts_neutral():
    engine = TrustEngine()
    entity = engine.register_entity("PC-01")
    assert entity.score == 70.0
    assert engine.get_trust_level("PC-01") == "NORMAL"


def test_trust_decreases_on_suspicious_behavior():
    engine = TrustEngine()
    engine.register_entity("PC-02")
    engine.update_trust("PC-02", reason="anomalous traffic spike", delta=-20)
    entity = engine.get_trust("PC-02")
    assert entity.score == 50.0
    assert engine.get_trust_level("PC-02") == "SUSPICIOUS"


def test_trust_increases_on_good_behavior():
    engine = TrustEngine()
    engine.register_entity("PC-03")
    engine.update_trust("PC-03", reason="successful authentication", delta=10)
    entity = engine.get_trust("PC-03")
    assert entity.score == 80.0
    assert engine.get_trust_level("PC-03") == "NORMAL"


def test_score_never_exceeds_bounds():
    engine = TrustEngine()
    engine.register_entity("PC-04", initial_score=95)
    engine.update_trust("PC-04", reason="repeated good behavior", delta=50)
    assert engine.get_trust("PC-04").score == 100.0

    engine.register_entity("PC-05", initial_score=5)
    engine.update_trust("PC-05", reason="critical incident", delta=-50)
    assert engine.get_trust("PC-05").score == 0.0


def test_repeated_suspicious_events_trigger_decay():
    engine = TrustEngine()
    engine.register_entity("PC-06")
    engine.update_trust("PC-06", reason="anomaly 1", delta=-5)
    engine.update_trust("PC-06", reason="anomaly 2", delta=-5)
    entity = engine.get_trust("PC-06")
    assert entity.score == 55.0
    assert entity.consecutive_suspicious_events == 0


def test_sustained_normal_behavior_triggers_recovery():
    engine = TrustEngine()
    engine.register_entity("PC-07", initial_score=50)
    engine.update_trust("PC-07", reason="normal auth 1", delta=1)
    engine.update_trust("PC-07", reason="normal auth 2", delta=1)
    engine.update_trust("PC-07", reason="normal auth 3", delta=1)
    entity = engine.get_trust("PC-07")
    assert entity.score == 55.0