"""Study 2 baselines. Designs use the public interface (names, describe, train, test). All are analysed
with the exact posterior (env/ideal.py); env.task_of only relabels names to internal ids for that analysis,
which carries no information about the learner."""
import numpy as np

from env import ideal, tasks
from harness.baselines import public_view


def analyse_and_submit(env):
    verdict = ideal.ideal_verdict(env.test_events(), env.cfg, env.sim)
    env.submit(verdict)
    return verdict


def random_interleaved(env, seed):
    rng = np.random.default_rng(seed)
    names, _ = public_view(env)
    p_train = env.cfg["study2"]["baselines"]["random_interleaved_p_train"]
    trained = set()
    while env.budget > 0:
        untrained = [n for n in names if n not in trained]
        if untrained and rng.random() < p_train:
            n = untrained[rng.integers(len(untrained))]
            env.train([n])
            trained.add(n)
        else:
            env.test(names[rng.integers(len(names))])
    return analyse_and_submit(env)


def train_first(env, seed):
    rng = np.random.default_rng(seed)
    names, _ = public_view(env)
    lo, hi = env.cfg["study2"]["baselines"]["train_first_sizes"]
    m = int(rng.integers(lo, hi + 1))
    env.train([names[i] for i in rng.choice(len(names), size=m, replace=False)])
    while env.budget > 0:
        env.test(names[rng.integers(len(names))])
    return analyse_and_submit(env)


def scripted_design(sim, rng, n_candidates):
    """Target T and 3 stages of 3 training tasks; each training task contains exactly one of T's rules.
    Among random candidates, keep the one with the lowest similarity of T to all 9 training tasks."""
    best = None
    all_parts = [tasks.task_parts(t) for t in range(64)]
    for _ in range(n_candidates):
        t = int(rng.integers(64))
        tp = all_parts[t]
        stages, used, ok = [], set(), True
        for _stage in range(3):
            stage = []
            for d in range(tasks.N_DIMS):
                pool = [u for u in range(64) if u not in used and all_parts[u][d] == tp[d]
                        and all(all_parts[u][e] != tp[e] for e in range(tasks.N_DIMS) if e != d)]
                if not pool:
                    ok = False
                    break
                u = int(pool[rng.integers(len(pool))])
                stage.append(u)
                used.add(u)
            if not ok:
                break
            stages.append(stage)
        if not ok:
            continue
        score = float(sim[t, sorted(used)].max())
        if best is None or score < best[0]:
            best = (score, t, stages)
    return best[1], best[2]


def scripted(env, seed):
    rng = np.random.default_rng(seed)
    b = env.cfg["study2"]["baselines"]
    target, stages = scripted_design(env.sim, rng, b["scripted_n_candidates"])
    for stage in stages:
        env.train([env.name(u) for u in stage])
        for _ in range(b["scripted_repeats"]):
            env.test(env.name(target))
    return analyse_and_submit(env)


BASELINES = {"scripted": scripted, "random_interleaved": random_interleaved, "train_first": train_first}
