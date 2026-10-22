"""Study 2: exact posterior over the learners given test data (all parameters known except k).

Likelihood of one test result y with mean mu: P(y) = Phi((y + 0.5 - mu)/sd) - Phi((y - 0.5 - mu)/sd) for y > 1,
and Phi((1.5 - mu)/sd) for y = 1 (rounding and the floor at 1).
"""
import numpy as np
from scipy.stats import norm

from env import learners

VERDICT = {"part_based": "part-based", "holistic": "holistic", "factor_when_justified": "factor-when-justified"}


def hypotheses(cfg):
    """(learner, k, prior weight) for every hypothesis."""
    prior = cfg["study2"]["prior"]
    ks = cfg["study2"]["k_values"]
    out = [("part_based", None, prior["part_based"]), ("holistic", None, prior["holistic"])]
    out += [("factor_when_justified", k, prior["factor_when_justified"] / len(ks)) for k in ks]
    return out


def log_likelihood(events, learner, k, cfg, sim):
    sd, floor = cfg["noise"]["sd"], cfg["noise"]["min_cost"]
    total = 0.0
    cache = {}
    for t, known, y in events:
        key = (t, known)
        if key not in cache:
            cache[key] = learners.mean_cost(learner, t, list(known), cfg, sim, k)
        mu = cache[key]
        if y <= floor:
            p = norm.cdf((floor + 0.5 - mu) / sd)
        else:
            p = norm.cdf((y + 0.5 - mu) / sd) - norm.cdf((y - 0.5 - mu) / sd)
        total += np.log(max(p, 1e-300))
    return total


def posterior(events, cfg, sim):
    """Posterior over the three verdicts, and over the four hypotheses (k separate)."""
    hyps = hypotheses(cfg)
    logp = np.array([np.log(w) + log_likelihood(events, l, k, cfg, sim) for l, k, w in hyps])
    p = np.exp(logp - logp.max())
    p /= p.sum()
    detail = {f"{l}" + (f"_k{k}" if k else ""): float(q) for (l, k, _), q in zip(hyps, p)}
    verdicts = {}
    for (l, _, _), q in zip(hyps, p):
        verdicts[VERDICT[l]] = verdicts.get(VERDICT[l], 0.0) + float(q)
    return verdicts, detail


def ideal_verdict(events, cfg, sim):
    verdicts, detail = posterior(events, cfg, sim)
    best = max(verdicts, key=verdicts.get)
    return {"verdict": best, "confidence": verdicts[best],
            "justification": "ideal analysis; posterior " + ", ".join(f"{k} {v:.3f}" for k, v in detail.items())}
