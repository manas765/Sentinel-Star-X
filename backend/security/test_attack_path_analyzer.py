import networkx as nx

from security.attack_path_analyzer import AttackPathAnalyzer


def _star_topology() -> nx.Graph:
    """SWITCH is the hub; PC-1..PC-4 are spokes, matching the project's Star topology."""
    g = nx.Graph()
    g.add_edges_from([
        ("SWITCH", "PC-1"),
        ("SWITCH", "PC-2"),
        ("SWITCH", "PC-3"),
        ("SWITCH", "PC-4"),
    ])
    return g


def test_no_paths_from_unknown_node():
    analyzer = AttackPathAnalyzer(_star_topology())
    paths = analyzer.find_attack_paths("GHOST-NODE", {})
    assert paths == []


def test_finds_paths_to_all_reachable_nodes():
    analyzer = AttackPathAnalyzer(_star_topology())
    paths = analyzer.find_attack_paths("PC-1", {})
    targets = {p.target for p in paths}
    assert targets == {"SWITCH", "PC-2", "PC-3", "PC-4"}


def test_direct_neighbor_has_fewer_hops_than_indirect():
    analyzer = AttackPathAnalyzer(_star_topology())
    paths = analyzer.find_attack_paths("PC-1", {})
    direct = next(p for p in paths if p.target == "SWITCH")
    indirect = next(p for p in paths if p.target == "PC-2")
    assert direct.hop_count == 1
    assert indirect.hop_count == 2


def test_path_through_high_threat_node_ranks_higher():
    analyzer = AttackPathAnalyzer(_star_topology())
    # Compare a path through a high-threat node vs the same-length path with no threat
    high_threat_paths = analyzer.find_attack_paths("PC-1", {"SWITCH": 0.9})
    no_threat_paths = analyzer.find_attack_paths("PC-1", {})

    to_pc2_high = next(p for p in high_threat_paths if p.target == "PC-2")
    to_pc2_none = next(p for p in no_threat_paths if p.target == "PC-2")

    assert to_pc2_high.risk_score > to_pc2_none.risk_score

def test_highest_risk_targets_respects_top_n():
    analyzer = AttackPathAnalyzer(_star_topology())
    top = analyzer.highest_risk_targets("PC-1", {"SWITCH": 0.9}, top_n=2)
    assert len(top) == 2
    assert top[0].risk_score >= top[1].risk_score