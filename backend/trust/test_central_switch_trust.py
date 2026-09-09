from trust.trust_engine import TrustEngine
from trust.central_switch_trust import CentralSwitchTrustMonitor, SwitchMetrics


def test_healthy_switch_keeps_high_trust():
    engine = TrustEngine()
    monitor = CentralSwitchTrustMonitor(engine)
    metrics = SwitchMetrics(
        switch_id="SWITCH-01",
        cpu_percent=30.0,
        memory_percent=40.0,
        packet_loss_percent=0.1,
        latency_ms=10.0,
        failure_risk=0.05,
    )
    monitor.evaluate(metrics)
    entity = engine.get_trust("SWITCH-01")
    assert entity.score > 70.0
    assert engine.get_trust_level("SWITCH-01") in ("NORMAL", "TRUSTED")


def test_critical_cpu_drops_trust_significantly():
    engine = TrustEngine()
    monitor = CentralSwitchTrustMonitor(engine)
    metrics = SwitchMetrics(
        switch_id="SWITCH-02",
        cpu_percent=95.0,
        memory_percent=40.0,
        packet_loss_percent=0.1,
        latency_ms=10.0,
        failure_risk=0.05,
    )
    monitor.evaluate(metrics)
    entity = engine.get_trust("SWITCH-02")
    assert entity.score < 70.0


def test_high_failure_risk_and_security_risk_compound():
    engine = TrustEngine()
    monitor = CentralSwitchTrustMonitor(engine)
    metrics = SwitchMetrics(
        switch_id="SWITCH-03",
        cpu_percent=30.0,
        memory_percent=30.0,
        packet_loss_percent=0.1,
        latency_ms=10.0,
        failure_risk=0.8,
        security_risk=0.6,
    )
    monitor.evaluate(metrics)
    entity = engine.get_trust("SWITCH-03")
    # both failure risk critical (-15) and security risk (-15) should apply
    assert entity.score <= 70.0 - 15 - 15 + 0.5 * 3  # allow for the 3 normal-metric +0.5 bumps