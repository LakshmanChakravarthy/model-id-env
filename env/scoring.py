"""Scores for a finished instance: verdict correct, dissociation, Brier."""
import numpy as np

from env import tasks
from env.environment import CORRECT_VERDICT


def dissociation(events, sim, cfg):
    """1 - |corr(new_parts, similarity)| over unique (task, training state) pairs tested."""
    unique = sorted({(t, known) for t, known, _ in events})
    if len(unique) < 2:
        return 0.0
    newp = np.array([tasks.new_parts(t, known) for t, known in unique], dtype=float)
    s = np.array([tasks.similarity_to_known(t, known, sim, cfg["similarity"]["measure"],
                                            cfg["similarity"]["kernel_tau"]) for t, known in unique])
    const_p, const_s = newp.std() == 0, s.std() == 0
    if const_p and const_s:
        return 0.0
    if const_p or const_s:
        return 1.0
    return float(1.0 - abs(np.corrcoef(newp, s)[0, 1]))


def score(env):
    v = env.verdict
    correct = int(v is not None and v["verdict"] == CORRECT_VERDICT[(env.condition, env.learner)])
    brier = 0.25 if v is None else (v["confidence"] - correct) ** 2
    return {"correct": correct,
            "dissociation": dissociation(env.test_events(), env.sim, env.cfg),
            "brier": float(brier),
            "n_tests": len(env.test_events())}


def instance_record(env, scores, extra=None):
    """Everything about one instance, for results/<instance>.json."""
    return {"learner": env.learner, "condition": env.condition, "seed": env.seed, "config": env.cfg,
            "correct_verdict": CORRECT_VERDICT[(env.condition, env.learner)],
            "label_of": [lab.tolist() for lab in env.label_of],
            "log": env.log, "verdict": env.verdict, "scores": scores, **(extra or {})}
