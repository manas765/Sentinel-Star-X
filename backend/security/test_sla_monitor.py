from security.sla_monitor import SLAMonitor
from security.sla_models import SLATarget


def test_no_target_registered_is_always_compliant():
    monitor = SLAMonitor()
    status = monitor.evaluate("PC-60", uptime_percent=95.0, response_time_ms=500.0, packet_loss_percent=10.0)
    assert status.is_compliant is True


def test_meeting_all_targets_is_compliant():
    monitor = SLAMonitor()
    monitor.register_target(SLATarget(entity_id="APP-01", name="Web App"))
    status = monitor.evaluate("APP-01", uptime_percent=99.95, response_time_ms=150.0, packet_loss_percent=0.5)
    assert status.is_compliant is True
    assert status.violations == []


def test_response_time_violation_detected():
    monitor = SLAMonitor()
    monitor.register_target(SLATarget(entity_id="APP-02", name="API Service", max_response_time_ms=200.0))
    status = monitor.evaluate("APP-02", uptime_percent=99.95, response_time_ms=350.0, packet_loss_percent=0.5)
    assert status.is_compliant is False
    assert any(v.metric == "response_time_ms" for v in status.violations)


def test_severity_scales_with_overage():
    monitor = SLAMonitor()
    monitor.register_target(SLATarget(entity_id="APP-03", name="DB", max_response_time_ms=100.0))
    minor = monitor.evaluate("APP-03", uptime_percent=99.95, response_time_ms=105.0, packet_loss_percent=0.1)
    critical = monitor.evaluate("APP-03", uptime_percent=99.95, response_time_ms=250.0, packet_loss_percent=0.1)
    assert minor.violations[0].severity == "MINOR"
    assert critical.violations[0].severity == "CRITICAL"


def test_uptime_below_target_is_violation():
    monitor = SLAMonitor()
    monitor.register_target(SLATarget(entity_id="APP-04", name="Auth Service", uptime_target_percent=99.9))
    status = monitor.evaluate("APP-04", uptime_percent=98.0, response_time_ms=50.0, packet_loss_percent=0.1)
    assert status.is_compliant is False
    assert any(v.metric == "uptime_percent" for v in status.violations)


def test_multiple_violations_all_captured():
    monitor = SLAMonitor()
    monitor.register_target(SLATarget(entity_id="APP-05", name="Everything Broken"))
    status = monitor.evaluate("APP-05", uptime_percent=90.0, response_time_ms=1000.0, packet_loss_percent=20.0)
    assert len(status.violations) == 3