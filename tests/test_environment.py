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
    mapping = env.describe(env.name(t))["mapping"]
    assert list(mapping.values()) == tasks.response_matrix()[t].tolist()


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
