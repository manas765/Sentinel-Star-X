import pytest
from recovery.multi_stage_recovery import (
    MultiStageRecovery, RecoveryStage, StageStatus
)


@pytest.fixture
def msr():
    return MultiStageRecovery()


def always_succeeds(stage, ctx):
    return True, {"message": "ok"}

def always_fails(stage, ctx):
    return False, {"error": "simulated failure"}

def fails_on(stage_name):
    def executor(stage, ctx):
        if stage.name == stage_name:
            return False, {"error": f"{stage_name} failed"}
        return True, {"message": "ok"}
    return executor


def test_build_plan_reroute(msr):
    plan = msr.build_plan("A", "reroute")
    assert plan.node_id == "A"
    assert plan.strategy == "reroute"
    assert len(plan.stages) == 3

def test_build_plan_restart(msr):
    plan = msr.build_plan("A", "restart")
    assert len(plan.stages) == 4

def test_all_stages_pass(msr):
    plan = msr.build_plan("A", "reroute")
    result = msr.execute_plan(plan, always_succeeds)
    assert result.overall_success is True
    assert all(s.status == StageStatus.COMPLETED for s in result.stages)

def test_non_skippable_failure_aborts_plan(msr):
    plan = msr.build_plan("A", "reroute")
    result = msr.execute_plan(plan, fails_on("isolate"))
    assert result.overall_success is False
    assert result.stages[0].status == StageStatus.FAILED

def test_skippable_failure_continues_plan(msr):
    plan = msr.build_plan("A", "reroute")
    result = msr.execute_plan(plan, fails_on("verify"))
    assert result.overall_success is True
    verify_stage = next(s for s in result.stages if s.name == "verify")
    assert verify_stage.status == StageStatus.SKIPPED

def test_plan_is_complete_after_execution(msr):
    plan = msr.build_plan("A", "failover")
    result = msr.execute_plan(plan, always_succeeds)
    assert result.is_complete() is True

def test_summary_counts_correct(msr):
    plan = msr.build_plan("A", "restart")
    result = msr.execute_plan(plan, always_succeeds)
    summary = result.summary()
    assert summary["total_stages"] == 4
    assert summary["overall_success"] is True

def test_exception_in_executor_handled(msr):
    def raises(stage, ctx):
        raise RuntimeError("unexpected error")
    plan = msr.build_plan("A", "reroute")
    result = msr.execute_plan(plan, raises)
    assert result.overall_success is False
    assert result.stages[0].error is not None
