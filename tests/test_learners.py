import numpy as np

from env import learners, tasks
from env.config import load_config

CFG = load_config()
SIM = tasks.similarity_matrix(tasks.response_matrix())


def test_part_based_depends_only_on_parts():
    known = [tasks.task_id(0, 0, 0)]
    same_mapping = tasks.task_id(3, 0, 1)     # similarity 1, 2 new parts
    far = tasks.task_id(0, 0, 2)              # similarity 0, 1 new part
    pb = lambda t: learners.mean_cost("part_based", t, known, CFG, SIM)
    ho = lambda t: learners.mean_cost("holistic", t, known, CFG, SIM)
    assert pb(same_mapping) > pb(far)
    assert ho(same_mapping) < ho(far)
    assert ho(same_mapping) == CFG["holistic"]["base"]


def test_selection_uncertainty():
    known = [tasks.task_id(0, 0, 0), tasks.task_id(1, 1, 1)]
    assert learners.selection_uncertainty(tasks.task_id(0, 1, 2), known) == 2.0
    assert learners.selection_uncertainty(tasks.task_id(0, 0, 0), [tasks.task_id(0, 0, 0)]) == 0.0


def test_sample_cost_seeded_and_floored():
    known = [tasks.task_id(0, 0, 0)]
    a = [learners.sample_cost("holistic", 5, known, CFG, SIM, np.random.default_rng(1)) for _ in range(3)]
    b = [learners.sample_cost("holistic", 5, known, CFG, SIM, np.random.default_rng(1)) for _ in range(3)]
    assert a == b
    rng = np.random.default_rng(0)
    samples = [learners.sample_cost("part_based", 5, known, CFG, SIM, rng) for _ in range(2000)]
    assert min(samples) >= CFG["noise"]["min_cost"]
    assert abs(np.mean(samples) - learners.mean_cost("part_based", 5, known, CFG, SIM)) < 0.5
