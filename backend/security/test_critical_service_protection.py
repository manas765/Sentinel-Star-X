from security.critical_service_protection import CriticalServiceProtection
from security.critical_service_models import CriticalService
from security.threat_level_models import ThreatLevel


def test_unregistered_entity_is_not_critical():
    protection = CriticalServiceProtection()
    assert protection.is_critical("PC-40") is False


def test_registered_service_is_critical():
    protection = CriticalServiceProtection()
    protection.register_critical_service(
        CriticalService(entity_id="DB-01", name="Primary Database", priority=1)
    )
    assert protection.is_critical("DB-01") is True


def test_critical_service_requires_action_earlier_than_normal():
    protection = CriticalServiceProtection()
    protection.register_critical_service(
        CriticalService(entity_id="DB-01", name="Primary Database", priority=1)
    )
    status = protection.assess_protection("DB-01", ThreatLevel.SUSPICIOUS)
    assert status.requires_immediate_action is True


def test_normal_entity_does_not_require_action_at_same_level():
    protection = CriticalServiceProtection()
    status = protection.assess_protection("PC-41", ThreatLevel.SUSPICIOUS)
    assert status.requires_immediate_action is False


def test_normal_entity_requires_action_at_restrict():
    protection = CriticalServiceProtection()
    status = protection.assess_protection("PC-42", ThreatLevel.RESTRICT)
    assert status.requires_immediate_action is True


def test_dependent_impact_lists_affected_critical_services():
    protection = CriticalServiceProtection()
    protection.register_critical_service(
        CriticalService(
            entity_id="APP-01", name="Web App",
            dependent_services=["SWITCH", "DB-01"],
        )
    )
    impacted = protection.get_dependent_impact("SWITCH")
    assert impacted == ["APP-01"]