from security.red_vs_blue_simulator import RedVsBlueSimulator
from security.red_team_scenarios import brute_force_then_breach_scenario


def test_scenario_runs_all_steps():
    simulator = RedVsBlueSimulator()
    steps = brute_force_then_breach_scenario()
    report = simulator.run_scenario("brute_force_then_breach", steps)
    assert len(report.steps) == 4
    assert report.scenario_name == "brute_force_then_breach"


def test_baseline_step_stays_low_risk():
    simulator = RedVsBlueSimulator()
    steps = brute_force_then_breach_scenario()
    report = simulator.run_scenario("brute_force_then_breach", steps)
    baseline = report.steps[0]
    assert baseline.risk_score == 0.0
    assert baseline.threat_level == "NORMAL"


def test_threat_level_escalates_as_attack_progresses():
    simulator = RedVsBlueSimulator()
    steps = brute_force_then_breach_scenario()
    report = simulator.run_scenario("brute_force_then_breach", steps)
    first_level = report.steps[0].threat_level
    last_level = report.steps[-1].threat_level
    # Escalation should have occurred by the final, most severe step
    levels_order = ["NORMAL", "MONITOR", "SUSPICIOUS", "RESTRICT", "QUARANTINE", "EMERGENCY"]
    assert levels_order.index(last_level) > levels_order.index(first_level)


def test_final_step_has_highest_risk_score():
    simulator = RedVsBlueSimulator()
    steps = brute_force_then_breach_scenario()
    report = simulator.run_scenario("brute_force_then_breach", steps)
    scores = [s.risk_score for s in report.steps]
    assert scores[-1] == max(scores)


def test_report_helper_properties_work():
    simulator = RedVsBlueSimulator()
    steps = brute_force_then_breach_scenario()
    report = simulator.run_scenario("brute_force_then_breach", steps)
    assert report.final_threat_level == report.steps[-1].threat_level
    assert isinstance(report.survival_mode_was_triggered, bool)