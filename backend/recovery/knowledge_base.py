from __future__ import annotations
from typing import Dict, List, Optional
from .models import RecoveryEvent
from .memory import NetworkMemory


class RecoveryKnowledgeBase:
    """
    Feature #31 — Recovery Knowledge Base.

    Indexes past recovery events from NetworkMemory and answers
    questions like: "What strategy worked best when node X failed?"
    The Decision Engine (#22) queries this before choosing a strategy.
    """

    def __init__(self, memory: NetworkMemory) -> None:
        self._memory = memory

    def best_strategy_for_node(self, node_id: str) -> Optional[str]:
        """Return the strategy with the highest success rate for this node."""
        events = self._memory.events_for_node(node_id)
        if not events:
            return None
        strategy_stats: Dict[str, Dict] = {}
        for e in events:
            s = e.strategy_used
            if s not in strategy_stats:
                strategy_stats[s] = {"success": 0, "total": 0}
            strategy_stats[s]["total"] += 1
            if e.success:
                strategy_stats[s]["success"] += 1
        best = max(
            strategy_stats.items(),
            key=lambda x: x[1]["success"] / x[1]["total"]
        )
        return best[0]

    def fastest_successful_strategy(self, node_id: str) -> Optional[str]:
        """Return the strategy that recovered this node fastest on average."""
        events = [
            e for e in self._memory.events_for_node(node_id) if e.success
        ]
        if not events:
            return None
        strategy_times: Dict[str, List[float]] = {}
        for e in events:
            strategy_times.setdefault(e.strategy_used, []).append(e.duration_seconds)
        avg_times = {s: sum(t) / len(t) for s, t in strategy_times.items()}
        return min(avg_times, key=avg_times.__getitem__)

    def known_strategies(self) -> List[str]:
        """All strategies ever attempted."""
        return list({e.strategy_used for e in self._memory.get_events()})

    def strategy_summary(self) -> List[Dict]:
        """Success rate + avg duration for every known strategy."""
        results = []
        for strategy in self.known_strategies():
            events = self._memory.events_for_strategy(strategy)
            successful = [e for e in events if e.success]
            avg_duration = (
                sum(e.duration_seconds for e in successful) / len(successful)
                if successful else None
            )
            results.append({
                "strategy": strategy,
                "attempts": len(events),
                "successes": len(successful),
                "success_rate": len(successful) / len(events),
                "avg_duration_seconds": avg_duration,
            })
        return sorted(results, key=lambda x: x["success_rate"], reverse=True)

    def recommend(self, node_id: str) -> Dict:
        """
        Single entry point for the Decision Engine.
        Returns best strategy + reasoning.
        """
        best = self.best_strategy_for_node(node_id)
        fastest = self.fastest_successful_strategy(node_id)
        return {
            "node_id": node_id,
            "recommended_strategy": best,
            "fastest_strategy": fastest,
            "known_strategies": self.known_strategies(),
            "has_history": best is not None,
        }
