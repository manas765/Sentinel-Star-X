import pytest
from recovery.research_experiment import ResearchExperimentMode


@pytest.fixture
def rem():
    return ResearchExperimentMode()


@pytest.fixture
def experiment(rem):
    return rem.create_experiment(
        name="Test Experiment",
        description="Compare reroute vs restart",
        strategies=["reroute", "restart"],
        node_ids=["A", "B"],
        repeat_count=3,
    )


def test_create_experiment(rem, experiment):
    assert experiment.name == "Test Experiment"
    assert len(rem.list_experiments()) == 1


def test_record_run(rem, experiment):
    run = rem.record_run(experiment.experiment_id, "reroute", "A", True, 2.0)
    assert run.strategy == "reroute"
    assert len(rem.get_runs(experiment.experiment_id)) == 1


def test_analyse_picks_best(rem, experiment):
    for _ in range(3):
        rem.record_run(experiment.experiment_id, "reroute", "A", True, 2.0)
    for _ in range(3):
        rem.record_run(experiment.experiment_id, "restart", "A", False, 8.0)
    result = rem.analyse(experiment.experiment_id)
    assert result.best_strategy == "reroute"


def test_analyse_success_rates(rem, experiment):
    rem.record_run(experiment.experiment_id, "reroute", "A", True, 2.0)
    rem.record_run(experiment.experiment_id, "reroute", "A", False, 2.0)
    result = rem.analyse(experiment.experiment_id)
    assert result.results_by_strategy["reroute"]["success_rate"] == 0.5


def test_analyse_no_runs(rem, experiment):
    result = rem.analyse(experiment.experiment_id)
    assert result.best_strategy is None
    assert "Insufficient" in result.conclusion


def test_unknown_experiment_raises(rem):
    with pytest.raises(KeyError):
        rem.analyse("nonexistent-id")


def test_conclusion_not_empty(rem, experiment):
    rem.record_run(experiment.experiment_id, "reroute", "A", True, 2.0)
    result = rem.analyse(experiment.experiment_id)
    assert len(result.conclusion) > 0
