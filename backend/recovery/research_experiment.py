from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ExperimentConfig(BaseModel):
    """Configuration for one research experiment."""
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    strategies: List[str]           # strategies to test
    node_ids: List[str]             # nodes to run experiment on
    repeat_count: int = 5           # how many times to run each strategy
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = []


class ExperimentRun(BaseModel):
    """A single run within an experiment."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str
    strategy: str
    node_id: str
    success: bool
    duration_seconds: float
    metadata: Dict[str, Any] = {}
    ran_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExperimentResult(BaseModel):
    """Aggregated results for one experiment."""
    experiment_id: str
    name: str
    total_runs: int
    results_by_strategy: Dict[str, Dict]   # strategy -> {success_rate, avg_duration, runs}
    best_strategy: Optional[str] = None
    conclusion: str


class ResearchExperimentMode:
    """
    Feature #33 - Research Experiment Mode.
    Lets developers run controlled experiments to test recovery
    strategies under different conditions and compare results.
    Useful for tuning the Decision Engine weights and knowledge base.
    """

    def __init__(self) -> None:
        self._experiments: Dict[str, ExperimentConfig] = {}
        self._runs: List[ExperimentRun] = []

    def create_experiment(
        self,
        name: str,
        description: str,
        strategies: List[str],
        node_ids: List[str],
        repeat_count: int = 5,
        tags: List[str] = [],
    ) -> ExperimentConfig:
        exp = ExperimentConfig(
            name=name,
            description=description,
            strategies=strategies,
            node_ids=node_ids,
            repeat_count=repeat_count,
            tags=tags,
        )
        self._experiments[exp.experiment_id] = exp
        return exp

    def record_run(
        self,
        experiment_id: str,
        strategy: str,
        node_id: str,
        success: bool,
        duration_seconds: float,
        metadata: Dict[str, Any] = {},
    ) -> ExperimentRun:
        run = ExperimentRun(
            experiment_id=experiment_id,
            strategy=strategy,
            node_id=node_id,
            success=success,
            duration_seconds=duration_seconds,
            metadata=metadata,
        )
        self._runs.append(run)
        return run

    def analyse(self, experiment_id: str) -> ExperimentResult:
        exp = self._experiments.get(experiment_id)
        if exp is None:
            raise KeyError(f"Experiment {experiment_id} not found")

        runs = [r for r in self._runs if r.experiment_id == experiment_id]
        results_by_strategy: Dict[str, Dict] = {}

        for strategy in exp.strategies:
            strategy_runs = [r for r in runs if r.strategy == strategy]
            if not strategy_runs:
                results_by_strategy[strategy] = {
                    "runs": 0, "success_rate": 0.0, "avg_duration": None
                }
                continue
            success_rate = sum(1 for r in strategy_runs if r.success) / len(strategy_runs)
            avg_duration = sum(r.duration_seconds for r in strategy_runs) / len(strategy_runs)
            results_by_strategy[strategy] = {
                "runs": len(strategy_runs),
                "success_rate": round(success_rate, 3),
                "avg_duration": round(avg_duration, 2),
            }

        # Pick best by success rate, then speed
        best = max(
            results_by_strategy.items(),
            key=lambda x: (x[1]["success_rate"], -(x[1]["avg_duration"] or 9999))
        )
        best_strategy = best[0] if best[1]["runs"] > 0 else None

        conclusion = (
            f"Best strategy: '{best_strategy}' with "
            f"{best[1]['success_rate']:.0%} success rate "
            f"and {best[1]['avg_duration']}s avg duration."
            if best_strategy else "Insufficient data to draw conclusions."
        )

        return ExperimentResult(
            experiment_id=experiment_id,
            name=exp.name,
            total_runs=len(runs),
            results_by_strategy=results_by_strategy,
            best_strategy=best_strategy,
            conclusion=conclusion,
        )

    def list_experiments(self) -> List[ExperimentConfig]:
        return list(self._experiments.values())

    def get_runs(self, experiment_id: str) -> List[ExperimentRun]:
        return [r for r in self._runs if r.experiment_id == experiment_id]
