"""
backend/ai/test_whatif_engine.py
Run with: pytest backend/ai/test_whatif_engine.py -v
"""

from backend.ai.telemetry_sim import SyntheticTelemetryGenerator
from backend.ai.whatif_engine import simulate_what_if


def test_isolated_node_down_lowers_score_and_lists_target():
    gen = SyntheticTelemetryGenerator(num_leaves=4, seed=1)
    result = simulate_what_if(gen, "node_down", "leaf-1")
    assert result["score_delta"] < 0
    assert "leaf-1" in result["affected_nodes"]
    assert any("leaf-1" in e["target_id"] for e in result["explanations"])


def test_central_down_causes_bigger_drop_than_isolated_leaf():
    gen1 = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    gen2 = SyntheticTelemetryGenerator(num_leaves=4, seed=2)
    central_result = simulate_what_if(gen1, "node_down", gen1.central_node_id)
    leaf_result = simulate_what_if(gen2, "node_down", "leaf-0")
    assert central_result["score_delta"] <= leaf_result["score_delta"]


def test_link_congestion_scenario_lists_target_link():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=3)
    target_link = gen.topology.links[0].link_id
    result = simulate_what_if(gen, "link_congestion", target_link)
    assert target_link in result["affected_links"]


def test_unknown_scenario_raises():
    gen = SyntheticTelemetryGenerator(num_leaves=2, seed=4)
    try:
        simulate_what_if(gen, "not_a_real_scenario", "leaf-0")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_recommendation_is_a_string():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=5)
    result = simulate_what_if(gen, "node_down", "leaf-2")
    assert isinstance(result["recommendation"], str)
    assert len(result["recommendation"]) > 0


def test_baseline_and_projected_scores_present():
    gen = SyntheticTelemetryGenerator(num_leaves=3, seed=6)
    result = simulate_what_if(gen, "packet_loss", "leaf-0")
    assert 0.0 <= result["baseline_score"] <= 100.0
    assert 0.0 <= result["projected_score"] <= 100.0


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} tests passed.")