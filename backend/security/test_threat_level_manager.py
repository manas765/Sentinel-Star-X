from security.threat_level_manager import ThreatLevelManager
from security.threat_level_models import ThreatLevel


def test_starts_at_normal():
    manager = ThreatLevelManager()
    state = manager.get_state("PC-30")
    assert state.level == ThreatLevel.NORMAL


def test_high_risk_escalates_directly_to_correct_level():
    manager = ThreatLevelManager()
    state = manager.update("PC-31", risk_score=0.9)
    assert state.level == ThreatLevel.EMERGENCY


def test_moderate_risk_escalates_to_restrict():
    manager = ThreatLevelManager()
    state = manager.update("PC-32", risk_score=0.5)
    assert state.level == ThreatLevel.RESTRICT


def test_deescalation_happens_one_step_at_a_time():
    manager = ThreatLevelManager()
    manager.update("PC-33", risk_score=0.9)  # EMERGENCY
    state = manager.update("PC-33", risk_score=0.0)  # risk now looks NORMAL
    # Should only step down to QUARANTINE, not jump straight to NORMAL
    assert state.level == ThreatLevel.QUARANTINE


def test_repeated_low_risk_gradually_returns_to_normal():
    manager = ThreatLevelManager()
    manager.update("PC-34", risk_score=0.9)  # EMERGENCY
    for _ in range(5):
        state = manager.update("PC-34", risk_score=0.0)
    assert state.level == ThreatLevel.NORMAL


def test_history_is_recorded():
    manager = ThreatLevelManager()
    manager.update("PC-35", risk_score=0.3)
    state = manager.update("PC-35", risk_score=0.9)
    assert len(state.history) == 2
    assert state.history[-1].to_level == "EMERGENCY"