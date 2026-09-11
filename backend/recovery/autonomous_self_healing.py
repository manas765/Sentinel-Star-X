from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from recovery.memory import NetworkMemory
from recovery.decision_engine import MultiObjectiveDecisionEngine
from recovery.context_aware_recovery import RecoveryContext
from recovery.multi_stage_recovery import MultiStageRecovery, RecoveryPlan
from recovery.verifier import RecoveryVerifier
from recovery.safe_rollback import SafeRollback
from security.threat_level_models import ThreatLevel


class HealingOutcome(BaseModel):
    healing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    strategy_chosen: Optional[str] = None
    security_blocked: bool = False
    requires_manual_approval: bool = False
    recovery_success: Optional[bool] = None
    verification_passed: Optional[bool] = None
    rolled_back: bool = False
    reason: str = ""


class AutonomousSelfHealing:
    """
    Feature #27 - Autonomous Self-Healing.

    The top-level orchestrator for your track. When a node fails:
    1. Check security gate (Manas) — block if compromised
    2. Save rollback snapshot
    3. Ask Decision Engine which strategy to use
    4. Execute via Multi-Stage Recovery
    5. Verify the result
    6. Rollback if verification fails
    """

    def __init__(self, memory: NetworkMemory) -> None:
        self._memory = memory
        self._engine = MultiObjectiveDecisionEngine(memory)
        self._msr = MultiStageRecovery()
        self._verifier = RecoveryVerifier()
        self._rollback = SafeRollback()
        self._history: List[HealingOutcome] = []

    def heal(
        self,
        node_id: str,
        context: RecoveryContext,
        node_state: Dict,
        threat_level: ThreatLevel = ThreatLevel.NORMAL,
        security_gate=None,
        stage_executor=None,
    ) -> HealingOutcome:
        outcome = HealingOutcome(node_id=node_id)

        # Step 1 — Security gate check
        if security_gate is not None:
            gate = security_gate.check(node_id, threat_level)
            if not gate.allowed:
                outcome.security_blocked = True
                outcome.requires_manual_approval = gate.requires_manual_approval
                outcome.reason = gate.reason
                outcome.completed_at = datetime.now(timezone.utc)
                self._history.append(outcome)
                return outcome

        # Step 2 — Save rollback snapshot
        self._rollback.save(node_id, node_state)

        # Step 3 — Decision Engine picks strategy
        decision = self._engine.decide(node_id, context)
        outcome.strategy_chosen = decision.chosen_strategy

        # Step 4 — Execute via Multi-Stage Recovery
        plan = self._msr.build_plan(node_id, decision.chosen_strategy)
        executor = stage_executor or self._default_executor
        executed_plan = self._msr.execute_plan(plan, executor)
        outcome.recovery_success = executed_plan.overall_success

        if not executed_plan.overall_success:
            # Recovery failed — rollback
            self._rollback.rollback(node_id, reason="recovery_failed")
            outcome.rolled_back = True
            outcome.reason = "Recovery failed — rolled back to pre-recovery state."
            outcome.completed_at = datetime.now(timezone.utc)
            self._history.append(outcome)
            return outcome

        # Step 5 — Verify
        verification = self._verifier.verify(node_id, node_state)
        outcome.verification_passed = verification.success

        if not verification.success:
            # Verification failed — rollback
            self._rollback.rollback(node_id, reason="verification_failed")
            outcome.rolled_back = True
            outcome.reason = f"Verification failed (confidence: {verification.confidence:.0%}) — rolled back."
        else:
            outcome.reason = f"Healing successful. Strategy: {decision.chosen_strategy}. Confidence: {verification.confidence:.0%}."

        outcome.completed_at = datetime.now(timezone.utc)
        self._history.append(outcome)
        return outcome

    def _default_executor(self, stage, ctx):
        """Default executor — always succeeds (real impl would call network APIs)."""
        return True, {"message": f"Stage {stage.name} completed."}

    def history(self) -> List[HealingOutcome]:
        return list(self._history)
