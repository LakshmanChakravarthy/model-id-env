import numpy as np

from env import tasks
from env.config import load_config
from env.environment import Environment
from harness import baselines

CFG = load_config()


def test_public_view_matches_hidden_structure():
    env = Environment("holistic", 4, CFG)
    names, sim = baselines.public_view(env)
    hidden = tasks.similarity_matrix(tasks.response_matrix())
    ids = [env.task_of(n) for n in names]
    assert np.allclose(sim, hidden[np.ix_(ids, ids)])
    known = [names[3], names[40]]
    for n in names[:20]:
        npub, spub = baselines.predictors(n, known, names, sim, CFG)
        kid = [env.task_of(k) for k in known]
        assert npub == tasks.new_parts(env.task_of(n), kid)
        assert np.isclose(spub, tasks.similarity_to_known(env.task_of(n), kid, hidden))


def test_analyze_recovers_the_true_predictor():
    rng = np.random.default_rng(0)
    x = rng.integers(0, 4, 200)
    s = rng.random(200)
    parts = [(a, b, 10 + 10 * a + rng.normal(0, 1)) for a, b in zip(x, s)]
    holo = [(a, b, 10 + 30 * (1 - b) + rng.normal(0, 1)) for a, b in zip(x, s)]
    assert baselines.analyze(parts)["verdict"] == "part-based"
    assert baselines.analyze(holo)["verdict"] == "holistic"
    assert baselines.analyze(parts)["confidence"] > 0.99


def test_naive_analysis_recovers_unconfounded_predictor():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 4, 200)
    s = rng.random(200)
    parts = [(a, b, 10 + 10 * a + rng.normal(0, 1)) for a, b in zip(x, s)]
    holo = [(a, b, 10 + 30 * (1 - b) + rng.normal(0, 1)) for a, b in zip(x, s)]
    assert baselines.analyze_naive(parts)["verdict"] == "part-based"
    assert baselines.analyze_naive(holo)["verdict"] == "holistic"


def test_naive_analysis_is_fooled_by_a_confound():
    # Similarity nearly determined by new parts; cost depends on parts only, but the naive
    # analysis cannot tell the two apart: confidence stays low.
    rng = np.random.default_rng(2)
    x = rng.integers(0, 4, 100)
    s = 1 - x / 3 + rng.normal(0, 0.01, 100)
    recs = [(a, b, 10 + 10 * a + rng.normal(0, 5)) for a, b in zip(x, s)]
    assert baselines.analyze_naive(recs)["confidence"] < 0.9


def test_d_optimal_prefers_dissociating_points():
    x = np.array([[0, 0.0], [3, 1.0], [0, 1.0], [3, 0.0], [1, 0.5]])
    chosen, det = baselines.d_optimal_allocation(x, 20)
    assert set(chosen) <= {0, 1, 2, 3}
    assert {2, 3} <= set(chosen)


def test_baselines_spend_the_budget_and_submit():
    for f in (baselines.random_experimenter, baselines.oracle_experimenter):
        for analysis in baselines.ANALYSES:
            env = Environment("part_based", 2, CFG)
            v = f(env, 0, analysis)
            assert env.budget == 0 and env.verdict == v
