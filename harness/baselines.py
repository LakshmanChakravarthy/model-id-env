"""Random and oracle experimenters. Both use only the public interface (labels, describe, train, test)
and the same analysis: OLS of cost on [1, new_parts, similarity]."""
import itertools

import numpy as np
from scipy.stats import norm


def public_view(env):
    """Task names, and the similarity matrix computed from describe mappings."""
    dims = env.describe()["dimensions"]
    names = ["-".join(c) for c in itertools.product(*dims.values())]
    resp = np.array([list(env.describe(n)["mapping"].values()) for n in names])
    sim = (resp[:, None, :] == resp[None, :, :]).mean(axis=2)
    return names, sim


def new_parts(name, known_names):
    labels = name.split("-")
    known = [k.split("-") for k in known_names]
    return sum(not any(k[d] == labels[d] for k in known) for d in range(len(labels)))


def similarity(i, known_idx, sim, measure, tau):
    if not known_idx:
        return 0.0
    s = sim[i, known_idx]
    if measure == "max":
        return float(s.max())
    w = np.exp((s - s.max()) / tau)
    return float((w * s).sum() / w.sum())


def predictors(name, known_names, names, sim, cfg):
    idx = {n: i for i, n in enumerate(names)}
    s = similarity(idx[name], [idx[k] for k in known_names], sim,
                   cfg["similarity"]["measure"], cfg["similarity"]["kernel_tau"])
    return new_parts(name, known_names), s


def analyze(records):
    """records: list of (new_parts, similarity, cost). Returns the verdict dict."""
    x = np.array([[r[0], r[1]] for r in records], dtype=float)
    y = np.array([r[2] for r in records], dtype=float)
    t = np.zeros(2)
    keep = [j for j in range(2) if x[:, j].std() > 0]
    if keep and len(y) > len(keep) + 1:
        X = np.column_stack([np.ones(len(y))] + [x[:, j] for j in keep])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        dof = len(y) - X.shape[1]
        s2 = resid @ resid / dof
        cov = s2 * np.linalg.pinv(X.T @ X)
        for k, j in enumerate(keep):
            se = np.sqrt(cov[k + 1, k + 1])
            t[j] = beta[k + 1] / se if se > 0 else 0.0
    t_parts, t_sim = t[0], -t[1]
    p = norm.cdf((t_parts - t_sim) / np.sqrt(2))
    verdict = "part-based" if t_parts > t_sim else "holistic"
    return {"verdict": verdict, "confidence": float(max(p, 1 - p)),
            "justification": f"OLS t(new_parts) = {t_parts:.2f}, -t(similarity) = {t_sim:.2f}"}


def run_tests(env, names, sim, known, test_names):
    records = []
    for n in test_names:
        r = env.test(n)
        if "examples_to_criterion" not in r:
            break
        records.append((*predictors(n, known, names, sim, env.cfg), r["examples_to_criterion"]))
    return records


def random_experimenter(env, seed):
    rng = np.random.default_rng(seed)
    names, sim = public_view(env)
    k = env.cfg["baselines"]["train_size"]
    known = [names[i] for i in rng.choice(len(names), size=k, replace=False)]
    env.train(known)
    test_names = [names[i] for i in rng.integers(len(names), size=env.budget)]
    verdict = analyze(run_tests(env, names, sim, known, test_names))
    env.submit(verdict)
    return verdict


def d_optimal_allocation(x, n_tests):
    """Greedy allocation of n_tests over candidate points x (n_cand, 2) to maximize det(cov)."""
    n, sx, sxx = 0, np.zeros(2), np.zeros((2, 2))
    chosen, eps = [], 1e-6 * np.eye(2)
    for _ in range(n_tests):
        m = n + 1
        sx_c = sx[None, :] + x
        sxx_c = sxx[None, :, :] + x[:, :, None] * x[:, None, :]
        mean = sx_c / m
        cov = sxx_c / m - mean[:, :, None] * mean[:, None, :] + eps
        det = cov[:, 0, 0] * cov[:, 1, 1] - cov[:, 0, 1] * cov[:, 1, 0]
        j = int(np.argmax(det))
        chosen.append(j)
        n, sx, sxx = m, sx_c[j], sxx_c[j]
    final = sxx / n - np.outer(sx / n, sx / n)
    return chosen, float(np.linalg.det(final))


def oracle_experimenter(env, seed):
    rng = np.random.default_rng(seed)
    names, sim = public_view(env)
    k = env.cfg["baselines"]["train_size"]
    n_tests = env.budget - k * env.cfg["environment"]["train_cost_per_task"]
    best = None
    for _ in range(env.cfg["baselines"]["oracle_n_candidate_k"]):
        known = [names[i] for i in rng.choice(len(names), size=k, replace=False)]
        cands = [n for n in names if n not in known]
        x = np.array([predictors(n, known, names, sim, env.cfg) for n in cands], dtype=float)
        chosen, det = d_optimal_allocation(x, n_tests)
        if best is None or det > best[0]:
            best = (det, known, [cands[j] for j in chosen])
    env.train(best[1])
    verdict = analyze(run_tests(env, names, sim, best[1], best[2]))
    env.submit(verdict)
    return verdict
