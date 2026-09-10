from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ABTestRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy: str
    node_id: str
    success: bool
    duration_seconds: float
    ran_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ABTestResult(BaseModel):
    test_id: str
    strategy_a: str
    strategy_b: str
    runs_a: int
    runs_b: int
    success_rate_a: float
    success_rate_b: float
    avg_duration_a: float
    avg_duration_b: float
    winner: Optional[str] = None
    conclusion: str


class RecoveryABTesting:
    """
    Feature #32 - Recovery A/B Testing.
    Runs two recovery strategies against similar failures
    and tracks which one performs better over time.
    """

    def __init__(self, strategy_a: str, strategy_b: str) -> None:
        self.test_id = str(uuid.uuid4())
        self.strategy_a = strategy_a
        self.strategy_b = strategy_b
        self._runs: List[ABTestRun] = []

    def record(self, strategy: str, node_id: str, success: bool, duration_seconds: float) -> ABTestRun:
        run = ABTestRun(
            strategy=strategy,
            node_id=node_id,
            success=success,
            duration_seconds=duration_seconds,
        )
        self._runs.append(run)
        return run

    def _stats(self, strategy: str) -> Tuple[int, float, float]:
        runs = [r for r in self._runs if r.strategy == strategy]
        if not runs:
            return 0, 0.0, 0.0
        success_rate = sum(1 for r in runs if r.success) / len(runs)
        avg_duration = sum(r.duration_seconds for r in runs) / len(runs)
        return len(runs), round(success_rate, 3), round(avg_duration, 2)

    def result(self) -> ABTestResult:
        runs_a, sr_a, dur_a = self._stats(self.strategy_a)
        runs_b, sr_b, dur_b = self._stats(self.strategy_b)

        if runs_a == 0 and runs_b == 0:
            winner = None
            conclusion = "No data yet."
        elif runs_a == 0:
            winner = self.strategy_b
            conclusion = f"{self.strategy_b} wins — no data for {self.strategy_a}."
        elif runs_b == 0:
            winner = self.strategy_a
            conclusion = f"{self.strategy_a} wins — no data for {self.strategy_b}."
        elif sr_a > sr_b:
            winner = self.strategy_a
            conclusion = f"{self.strategy_a} wins with higher success rate ({sr_a:.0%} vs {sr_b:.0%})."
        elif sr_b > sr_a:
            winner = self.strategy_b
            conclusion = f"{self.strategy_b} wins with higher success rate ({sr_b:.0%} vs {sr_a:.0%})."
        elif dur_a < dur_b:
            winner = self.strategy_a
            conclusion = f"Tied on success rate — {self.strategy_a} wins on speed ({dur_a}s vs {dur_b}s)."
        elif dur_b < dur_a:
            winner = self.strategy_b
            conclusion = f"Tied on success rate — {self.strategy_b} wins on speed ({dur_b}s vs {dur_a}s)."
        else:
            winner = None
            conclusion = "No clear winner — strategies are equivalent."

        return ABTestResult(
            test_id=self.test_id,
            strategy_a=self.strategy_a,
            strategy_b=self.strategy_b,
            runs_a=runs_a,
            runs_b=runs_b,
            success_rate_a=sr_a,
            success_rate_b=sr_b,
            avg_duration_a=dur_a,
            avg_duration_b=dur_b,
            winner=winner,
            conclusion=conclusion,
        )

    def total_runs(self) -> int:
        return len(self._runs)
