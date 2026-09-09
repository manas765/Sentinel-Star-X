from __future__ import annotations
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class StageStatus(str, Enum):
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"
    SKIPPED   = "SKIPPED"


class RecoveryStage(BaseModel):
    """One step in a multi-stage recovery plan."""
    stage_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    status: StageStatus = StageStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    skippable: bool = False       # can we skip this if it fails?


class RecoveryPlan(BaseModel):
    """An ordered sequence of stages to recover a node."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    strategy: str
    stages: List[RecoveryStage]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    overall_success: Optional[bool] = None

    def current_stage(self) -> Optional[RecoveryStage]:
        for stage in self.stages:
            if stage.status in (StageStatus.PENDING, StageStatus.RUNNING):
                return stage
        return None

    def is_complete(self) -> bool:
        return all(
            s.status in (StageStatus.COMPLETED, StageStatus.SKIPPED, StageStatus.FAILED)
            for s in self.stages
        )

    def summary(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "node_id": self.node_id,
            "strategy": self.strategy,
            "total_stages": len(self.stages),
            "completed": sum(1 for s in self.stages if s.status == StageStatus.COMPLETED),
            "failed": sum(1 for s in self.stages if s.status == StageStatus.FAILED),
            "skipped": sum(1 for s in self.stages if s.status == StageStatus.SKIPPED),
            "overall_success": self.overall_success,
        }


# Stage executor type: takes stage + context, returns (success, result_dict)
StageExecutor = Callable[[RecoveryStage, Dict], tuple[bool, Dict]]


class MultiStageRecovery:
    """
    Feature #29 — Multi-Stage Recovery.

    Breaks recovery into ordered stages: isolate → diagnose → repair → verify.
    Each stage must pass before the next starts. Skippable stages are bypassed
    on failure so the plan keeps moving. Non-skippable failures abort the plan.
    """

    # Default stage templates per strategy
    STAGE_TEMPLATES: Dict[str, List[Dict]] = {
        "reroute": [
            {"name": "isolate",   "description": "Isolate the failed node from traffic.", "skippable": False},
            {"name": "reroute",   "description": "Redirect traffic through alternate paths.", "skippable": False},
            {"name": "verify",    "description": "Confirm traffic is flowing correctly.", "skippable": True},
        ],
        "restart": [
            {"name": "isolate",   "description": "Isolate the failed node.", "skippable": False},
            {"name": "diagnose",  "description": "Check logs and identify root cause.", "skippable": True},
            {"name": "restart",   "description": "Restart the node service.", "skippable": False},
            {"name": "verify",    "description": "Confirm node is healthy post-restart.", "skippable": True},
        ],
        "failover": [
            {"name": "isolate",   "description": "Isolate the primary node.", "skippable": False},
            {"name": "failover",  "description": "Promote standby node to primary.", "skippable": False},
            {"name": "sync",      "description": "Sync state to new primary.", "skippable": True},
            {"name": "verify",    "description": "Confirm failover was successful.", "skippable": True},
        ],
        "isolate": [
            {"name": "isolate",   "description": "Fully isolate the node from network.", "skippable": False},
            {"name": "verify",    "description": "Confirm node is unreachable.", "skippable": True},
        ],
    }

    def build_plan(self, node_id: str, strategy: str) -> RecoveryPlan:
        """Build a recovery plan for a node using the given strategy."""
        templates = self.STAGE_TEMPLATES.get(strategy, self.STAGE_TEMPLATES["isolate"])
        stages = [RecoveryStage(**t) for t in templates]
        return RecoveryPlan(node_id=node_id, strategy=strategy, stages=stages)

    def execute_plan(
        self,
        plan: RecoveryPlan,
        executor: StageExecutor,
        context: Optional[Dict] = None,
    ) -> RecoveryPlan:
        """
        Run each stage in order using the provided executor function.
        executor(stage, context) -> (success: bool, result: dict)
        """
        ctx = context or {}
        for stage in plan.stages:
            if stage.status != StageStatus.PENDING:
                continue

            stage.status = StageStatus.RUNNING
            stage.started_at = datetime.now(timezone.utc)

            try:
                success, result = executor(stage, ctx)
                stage.result = result
                stage.completed_at = datetime.now(timezone.utc)

                if success:
                    stage.status = StageStatus.COMPLETED
                else:
                    stage.status = StageStatus.FAILED
                    stage.error = result.get("error", "Stage failed.")
                    if not stage.skippable:
                        # Abort — mark remaining as skipped
                        for remaining in plan.stages:
                            if remaining.status == StageStatus.PENDING:
                                remaining.status = StageStatus.SKIPPED
                        plan.overall_success = False
                        plan.completed_at = datetime.now(timezone.utc)
                        return plan
                    else:
                        stage.status = StageStatus.SKIPPED

            except Exception as e:
                stage.status = StageStatus.FAILED
                stage.error = str(e)
                stage.completed_at = datetime.now(timezone.utc)
                if not stage.skippable:
                    for remaining in plan.stages:
                        if remaining.status == StageStatus.PENDING:
                            remaining.status = StageStatus.SKIPPED
                    plan.overall_success = False
                    plan.completed_at = datetime.now(timezone.utc)
                    return plan

        plan.overall_success = all(
            s.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
            for s in plan.stages
        )
        plan.completed_at = datetime.now(timezone.utc)
        return plan
