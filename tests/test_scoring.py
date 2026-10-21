import numpy as np

from env import scoring, tasks
from env.config import load_config
from env.environment import Environment

CFG = load_config()
SIM = tasks.similarity_matrix(tasks.response_matrix())


def test_dissociation_edge_cases():
    assert scoring.dissociation([], SIM, CFG) == 0.0
    assert scoring.dissociation([(5, (), 10), (5, (), 12)], SIM, CFG) == 0.0   # one unique pair
    # Empty K: new parts = 3 and similarity = 0 for every task -> both constant.
    assert scoring.dissociation([(5, (), 10), (6, (), 12)], SIM, CFG) == 0.0


def test_dissociation_regular_case():
    known = (0,)
    events = [(t, known, 1) for t in range(1, 20)]
    newp = [tasks.new_parts(t, known) for t in range(1, 20)]
    s = [tasks.similarity_to_known(t, known, SIM) for t in range(1, 20)]
    expected = 1 - abs(np.corrcoef(newp, s)[0, 1])
    assert np.isclose(scoring.dissociation(events, SIM, CFG), expected)


def test_score_correct_and_brier():
    env = Environment("part_based", 0, CFG)
    env.train([env.name(0)])
    env.test(env.name(1))
    env.submit({"verdict": "part-based", "confidence": 0.9})
    sc = scoring.score(env)
    assert sc["correct"] == 1 and np.isclose(sc["brier"], 0.01) and sc["n_tests"] == 1
    env2 = Environment("part_based", 0, CFG)
    env2.submit({"verdict": "cannot_decide", "confidence": 0.9})
    assert scoring.score(env2)["correct"] == 0 and np.isclose(scoring.score(env2)["brier"], 0.81)


def test_case4_correct_verdicts():
    for learner, verdict, correct in [("holistic", "holistic", 1), ("part_based", "cannot_decide", 1),
                                      ("factorized_holistic", "cannot_decide", 1), ("part_based", "part-based", 0)]:
        env = Environment(learner, 0, CFG, "case4")
        env.submit({"verdict": verdict, "confidence": 0.8})
        assert scoring.score(env)["correct"] == correct
    assert scoring.score(Environment("holistic", 0, CFG))["brier"] == 0.25   # no verdict


def test_decisive_pairs():
    known = (tasks.task_id(0, 0, 0),)
    a = tasks.task_id(1, 1, 1)   # 3 new parts, similarity > 0
    b = tasks.task_id(0, 0, 3)   # 1 new part, similarity 0
    assert SIM[a, known[0]] > 0 and SIM[b, known[0]] == 0
    # part-based: b cheaper; holistic: a cheaper -> one decisive pair (b, a) once each is tested 3 times
    events = [(a, known, 1)] * 3 + [(b, known, 1)] * 3
    assert scoring.decisive_pairs(events, SIM, CFG) == 1
    assert scoring.decisive_pairs(events[:-1], SIM, CFG) == 0
