import pytest
from recovery.service_resilience import ServiceLevelResilience


@pytest.fixture
def slr():
    s = ServiceLevelResilience()
    s.register("web")
    s.register("db")
    s.register("auth")
    return s


def test_all_up_initially(slr):
    assert slr.all_up() is True

def test_update_service_down(slr):
    slr.update("web", is_up=False)
    assert slr.all_up() is False

def test_report_all_healthy(slr):
    report = slr.report()
    assert report.services_up == 3
    assert report.services_down == 0
    assert report.overall_resilience_score == 100.0

def test_report_one_down(slr):
    slr.update("db", is_up=False)
    report = slr.report()
    assert report.services_down == 1
    assert report.overall_resilience_score < 100.0

def test_degraded_penalises_score(slr):
    slr.update("web", is_up=True, degraded=True)
    report = slr.report()
    assert report.overall_resilience_score < 100.0
    assert report.services_degraded == 1

def test_weakest_service_identified(slr):
    slr.update("auth", is_up=True, uptime_percent=60.0)
    report = slr.report()
    assert report.weakest_service == "auth"

def test_empty_report(empty_slr=None):
    from recovery.service_resilience import ServiceLevelResilience
    slr = ServiceLevelResilience()
    report = slr.report()
    assert report.total_services == 0
    assert report.overall_resilience_score == 100.0
