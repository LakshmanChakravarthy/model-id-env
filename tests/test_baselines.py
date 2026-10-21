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


def test_d_optimal_prefers_dissociating_points():
    x = np.array([[0, 0.0], [3, 1.0], [0, 1.0], [3, 0.0], [1, 0.5]])
    chosen, det = baselines.d_optimal_allocation(x, 20)
    assert set(chosen) <= {0, 1, 2, 3}
    assert {2, 3} <= set(chosen)


def test_baselines_spend_the_budget_and_submit():
    for f in (baselines.random_experimenter, baselines.oracle_experimenter):
        env = Environment("part_based", 2, CFG)
        v = f(env, 0)
        assert env.budget == 0 and env.verdict == v
