from security.incident_report_generator import IncidentReportGenerator
from security.red_vs_blue_simulator import RedVsBlueSimulator
from security.red_team_scenarios import brute_force_then_breach_scenario


def _run_simulation():
    simulator = RedVsBlueSimulator()
    steps = brute_force_then_breach_scenario()
    return simulator.run_scenario("brute_force_then_breach", steps)


def test_report_has_unique_incrementing_ids():
    generator = IncidentReportGenerator()
    sim = _run_simulation()
    report1 = generator.generate_from_simulation(sim)
    report2 = generator.generate_from_simulation(sim)
    assert report1.report_id != report2.report_id


def test_report_captures_correct_entity():
    generator = IncidentReportGenerator()
    sim = _run_simulation()
    report = generator.generate_from_simulation(sim)
    assert report.entity_id == "PC-99"


def test_report_has_all_sections():
    generator = IncidentReportGenerator()
    sim = _run_simulation()
    report = generator.generate_from_simulation(sim)
    headings = [s.heading for s in report.sections]
    assert "Timeline" in headings
    assert "Outcome" in headings
    assert "Recommended follow-up" in headings


def test_timeline_lists_all_steps():
    generator = IncidentReportGenerator()
    sim = _run_simulation()
    report = generator.generate_from_simulation(sim)
    timeline = next(s.content for s in report.sections if s.heading == "Timeline")
    assert timeline.count("\n") == 3  # 4 steps -> 3 newlines between them


def test_to_text_produces_readable_string():
    generator = IncidentReportGenerator()
    sim = _run_simulation()
    report = generator.generate_from_simulation(sim)
    text = report.to_text()
    assert "INCIDENT REPORT" in text
    assert report.report_id in text