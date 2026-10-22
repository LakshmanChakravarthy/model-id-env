import numpy as np

from env import ideal, learners, scoring, tasks
from env.config import load_config
from env.environment import Environment
from harness import baselines_study2

CFG = load_config()
SIM = tasks.similarity_matrix(tasks.response_matrix())


def test_factored_library_threshold():
    known = [tasks.task_id(0, 0, 0), tasks.task_id(0, 1, 1), tasks.task_id(1, 1, 2)]
    lib2 = learners.factored_library(known, 2)
    assert lib2 == {(0, 0), (1, 1)}
    assert learners.factored_library(known, 3) == set()


def test_factor_learner_is_cheaper_route_and_bounds():
    rng = np.random.default_rng(0)
    for _ in range(50):
        known = [int(u) for u in rng.choice(64, size=6, replace=False)]
        t = int(rng.integers(64))
        f = learners.mean_cost("factor_when_justified", t, known, CFG, SIM, 2)
        h = learners.mean_cost("holistic", t, known, CFG, SIM)
        assert f <= h + 1e-9
    # With k = 1 and no holistic advantage, the part route equals the part-based learner.
    known = [tasks.task_id(0, 0, 0)]
    t = tasks.task_id(0, 0, 3)  # similarity 0
    assert learners.mean_cost("factor_when_justified", t, known, CFG, SIM, 1) == \
        learners.mean_cost("part_based", t, known, CFG, SIM)


def test_environment_k_hidden_and_seeded():
    a = Environment("factor_when_justified", 3, CFG, "study2")
    b = Environment("factor_when_justified", 3, CFG, "study2")
    assert a.k == b.k and a.k in CFG["study2"]["k_values"]
    assert Environment("factor_when_justified", 3, CFG, "study2", k=3).k == 3
    assert Environment("holistic", 3, CFG, "study2").k is None


def test_ideal_posterior_recovers_learner_from_noise_free_data():
    target, stages = baselines_study2.scripted_design(SIM, np.random.default_rng(1), 100)
    for learner, k in [("part_based", None), ("holistic", None), ("factor_when_justified", 2),
                       ("factor_when_justified", 3)]:
        events, known = [], []
        for stage in stages:
            known = known + stage
            mu = learners.mean_cost(learner, target, known, CFG, SIM, k)
            events += [(target, tuple(known), int(round(mu)))] * 12
        post, _ = ideal.posterior(events, CFG, SIM)
        assert max(post, key=post.get) == ideal.VERDICT[learner]


def test_baselines_run_and_score():
    for name, f in baselines_study2.BASELINES.items():
        env = Environment("factor_when_justified", 5, CFG, "study2", k=2)
        f(env, 1)
        s = scoring.score(env)
        assert 0.0 <= s["design_score"] <= 1.0 and env.verdict is not None
        assert s["inference_gap"] is not None
