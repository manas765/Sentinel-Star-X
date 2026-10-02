"""
backend/ai/test_benchmarking_engine.py
Run with: pytest backend/ai/test_benchmarking_engine.py -v
"""

from backend.ai.benchmarking_engine import BenchmarkingEngine, run_benchmark


def test_report_structure():
    report = run_benchmark(num_leaves=5, trials_per_scenario=2)
    assert "node_detection" in report
    assert "link_detection" in report
    assert "classification_accuracy" in report
    assert "root_cause_attribution_accuracy" in report
    assert "avg_detection_latency_ms" in report
    assert report["scenarios_run"] > 0


def test_node_detection_perfect_on_current_thresholds():
    report = run_benchmark(num_leaves=5, trials_per_scenario=5)
    nd = report["node_detection"]
    assert nd["false_positives"] == 0
    assert nd["false_negatives"] == 0
    assert nd["precision"] == 1.0
    assert nd["recall"] == 1.0


def test_link_detection_perfect_on_current_thresholds():
    report = run_benchmark(num_leaves=5, trials_per_scenario=5)
    ld = report["link_detection"]
    assert ld["false_positives"] == 0
    assert ld["false_negatives"] == 0
    assert ld["precision"] == 1.0
    assert ld["recall"] == 1.0


def test_classification_accuracy_perfect():
    report = run_benchmark(num_leaves=5, trials_per_scenario=5)
    assert report["classification_accuracy"] == 1.0
    assert report["classification_samples"] > 0


def test_root_cause_attribution_accuracy_perfect():
    report = run_benchmark(num_leaves=5, trials_per_scenario=5)
    assert report["root_cause_attribution_accuracy"] == 1.0
    assert report["root_cause_samples"] > 0


def test_results_deterministic_across_runs_excluding_latency():
    r1 = run_benchmark(num_leaves=5, trials_per_scenario=3)
    r2 = run_benchmark(num_leaves=5, trials_per_scenario=3)
    r1.pop("avg_detection_latency_ms")
    r2.pop("avg_detection_latency_ms")
    assert r1 == r2


def test_detection_latency_is_fast():
    report = run_benchmark(num_leaves=5, trials_per_scenario=3)
    assert report["avg_detection_latency_ms"] < 50


def test_custom_trial_count_scales_sample_size():
    small = BenchmarkingEngine(num_leaves=5, trials_per_scenario=2).run()
    large = BenchmarkingEngine(num_leaves=5, trials_per_scenario=6).run()
    assert large.scenarios_run > small.scenarios_run
    assert large.classification_samples > small.classification_samples


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")