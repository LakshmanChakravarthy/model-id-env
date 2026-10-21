import numpy as np
import pytest

from env import tasks
from env.config import load_config
from env.environment import Environment

CFG = load_config()


def test_names_roundtrip_and_permutation():
    env = Environment("holistic", 3, CFG)
    for t in range(64):
        assert env.task_of(env.name(t)) == t
    assert [l.tolist() for l in Environment("holistic", 3, CFG).label_of] == [l.tolist() for l in env.label_of]
    assert any(Environment("holistic", s, CFG).name(0) != env.name(0) for s in range(4, 10))
    with pytest.raises(ValueError):
        env.task_of("L9-S1-M1")


def test_budget_accounting():
    env = Environment("part_based", 0, CFG)
    b = env.budget
    env.describe()
    env.describe(env.name(5))
    env.get_budget()
    assert env.budget == b
    env.train([env.name(1), env.name(2)])
    assert env.budget == b - 2
    env.test(env.name(3))
    assert env.budget == b - 3
    env.budget = 0
    assert "error" in env.test(env.name(3))
    assert len(env.log) == 6


def test_describe_mapping_matches_hidden_task():
    env = Environment("part_based", 1, CFG)
    t = 37
    responses = env.describe(env.name(t))["responses"]
    assert [int(c) for c in responses] == tasks.response_matrix()[t].tolist()
    # Input i in binary = stimulus 1 features, then stimulus 2 features.
    i = 0b10100110
    assert tasks.all_inputs()[i].ravel().tolist() == [1, 0, 1, 0, 0, 1, 1, 0]


def test_compare_is_free_and_matches_similarity():
    env = Environment("holistic", 2, CFG)
    b = env.budget
    r = env.compare(env.name(3), env.name(7))
    assert r["fraction_same_response"] == tasks.similarity_matrix(tasks.response_matrix())[3, 7]
    assert env.budget == b


def test_same_seed_same_samples():
    a, b = Environment("holistic", 9, CFG), Environment("holistic", 9, CFG)
    for env in (a, b):
        env.train([env.name(0)])
    assert [a.test(a.name(5)) for _ in range(5)] == [b.test(b.name(5)) for _ in range(5)]


def test_submit_validation_and_closing():
    env = Environment("holistic", 0, CFG)
    with pytest.raises(ValueError):
        env.submit({"verdict": "maybe", "confidence": 0.5})
    with pytest.raises(ValueError):
        env.submit({"verdict": "holistic", "confidence": 1.5})
    env.submit({"verdict": "holistic", "confidence": 0.8, "justification": "x"})
    with pytest.raises(RuntimeError):
        env.test(env.name(0))


def test_case4_learner_only_in_case4():
    Environment("factorized_holistic", 0, CFG, "case4")
    with pytest.raises(ValueError):
        Environment("factorized_holistic", 0, CFG)
