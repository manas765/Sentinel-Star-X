from security.survival_mode_manager import SurvivalModeManager
from security.critical_service_protection import CriticalServiceProtection
from security.critical_service_models import CriticalService
from security.threat_level_models import ThreatLevel


def _setup_with_critical_services(count: int) -> CriticalServiceProtection:
    protection = CriticalServiceProtection()
    for i in range(count):
        protection.register_critical_service(
            CriticalService(entity_id=f"CRIT-{i}", name=f"Critical Service {i}")
        )
    return protection


def test_stays_inactive_when_everything_normal():
    protection = _setup_with_critical_services(4)
    manager = SurvivalModeManager(protection)
    levels = {f"CRIT-{i}": ThreatLevel.NORMAL for i in range(4)}
    state = manager.update(levels)
    assert state.is_active is False


def test_activates_when_majority_of_critical_services_at_risk():
    protection = _setup_with_critical_services(4)
    manager = SurvivalModeManager(protection)
    levels = {
        "CRIT-0": ThreatLevel.RESTRICT,
        "CRIT-1": ThreatLevel.QUARANTINE,
        "CRIT-2": ThreatLevel.NORMAL,
        "CRIT-3": ThreatLevel.NORMAL,
    }
    state = manager.update(levels)
    assert state.is_active is True


def test_activates_on_network_wide_threat_even_if_critical_services_fine():
    protection = _setup_with_critical_services(2)
    manager = SurvivalModeManager(protection)
    levels = {
        "CRIT-0": ThreatLevel.NORMAL,
        "CRIT-1": ThreatLevel.NORMAL,
        "PC-1": ThreatLevel.RESTRICT,
        "PC-2": ThreatLevel.RESTRICT,
        "PC-3": ThreatLevel.RESTRICT,
        "PC-4": ThreatLevel.NORMAL,
        "PC-5": ThreatLevel.NORMAL,
    }
    state = manager.update(levels)
    assert state.is_active is True


def test_does_not_deactivate_immediately_after_partial_recovery():
    protection = _setup_with_critical_services(2)
    manager = SurvivalModeManager(protection)
    manager.update({"CRIT-0": ThreatLevel.QUARANTINE, "CRIT-1": ThreatLevel.QUARANTINE})
    assert manager.state.is_active is True

    # Only partial improvement — still above the safety margin for deactivation
    state = manager.update({"CRIT-0": ThreatLevel.RESTRICT, "CRIT-1": ThreatLevel.NORMAL})
    assert state.is_active is True


def test_deactivates_once_well_below_thresholds():
    protection = _setup_with_critical_services(2)
    manager = SurvivalModeManager(protection)
    manager.update({"CRIT-0": ThreatLevel.QUARANTINE, "CRIT-1": ThreatLevel.QUARANTINE})
    assert manager.state.is_active is True

    state = manager.update({"CRIT-0": ThreatLevel.NORMAL, "CRIT-1": ThreatLevel.NORMAL})
    assert state.is_active is False


def test_history_records_both_transitions():
    protection = _setup_with_critical_services(2)
    manager = SurvivalModeManager(protection)
    manager.update({"CRIT-0": ThreatLevel.QUARANTINE, "CRIT-1": ThreatLevel.QUARANTINE})
    manager.update({"CRIT-0": ThreatLevel.NORMAL, "CRIT-1": ThreatLevel.NORMAL})
    assert len(manager.state.history) == 2
    assert manager.state.history[0].action == "ACTIVATED"
    assert manager.state.history[1].action == "DEACTIVATED"