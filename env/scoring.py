"""Scores for a finished instance: verdict correct, dissociation, Brier."""
import numpy as np

from collections import Counter

from env import learners, tasks
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


def decisive_pairs(events, sim, cfg):
    """Pairs of tested conditions (A, B) where part-based predicts A cheaper and holistic (mapping similarity)
    predicts B cheaper, each by more than the margin, and both tested at least min_tests times."""
    sc = cfg["scoring"]
    counts = Counter((t, known) for t, known, _ in events)
    conds = [c for c, n in counts.items() if n >= sc["decisive_pair_min_tests"]]
    pb = [learners.mean_cost("part_based", t, list(k), cfg, sim) for t, k in conds]
    ho = [learners.mean_cost("holistic", t, list(k), cfg, sim) for t, k in conds]
    m = sc["decisive_pair_margin"]
    return sum(1 for a in range(len(conds)) for b in range(len(conds))
               if pb[b] - pb[a] > m and ho[a] - ho[b] > m)


def score(env):
    v = env.verdict
    correct = int(v is not None and v["verdict"] == CORRECT_VERDICT[(env.condition, env.learner)])
    brier = 0.25 if v is None else (v["confidence"] - correct) ** 2
    n_dec = decisive_pairs(env.test_events(), env.sim, env.cfg)
    extra = {}
    if env.condition == "study2":
        from env import ideal
        post, detail = ideal.posterior(env.test_events(), env.cfg, env.sim)
        truth = CORRECT_VERDICT[(env.condition, env.learner)]
        best = max(post, key=post.get)
        extra = {"k": env.k, "ideal_posterior": post, "ideal_posterior_detail": detail,
                 "design_score": post[truth], "ideal_correct": int(best == truth),
                 "inference_gap": (None if v is None or v["verdict"] not in post
                                   else v["confidence"] - post[v["verdict"]])}
    return {**extra, "correct": correct,
            "dissociation": dissociation(env.test_events(), env.sim, env.cfg),
            "n_decisive_pairs": n_dec,
            "has_decisive_pair": int(n_dec > 0),
            "brier": float(brier),
            "n_tests": len(env.test_events())}


def instance_record(env, scores, extra=None):
    """Everything about one instance, for results/<instance>.json."""
    return {"learner": env.learner, "condition": env.condition, "seed": env.seed, "config": env.cfg,
            "correct_verdict": CORRECT_VERDICT[(env.condition, env.learner)],
            "label_of": [lab.tolist() for lab in env.label_of],
            "log": env.log, "verdict": env.verdict, "scores": scores, **(extra or {})}
