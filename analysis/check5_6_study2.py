"""Study 2 checks. Check 5: the regime change exists. Check 6: baselines (budget selection and confirmation).

Usage: python analysis/check5_6_study2.py check5 | check6
Writes results/checks/check5.json or check6.json.
"""
import itertools
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import learners, scoring, tasks
from env.config import load_config
from env.environment import Environment
from harness import baselines_study2

OUT = Path(__file__).resolve().parent.parent / "results" / "checks"
HYPS = [("part_based", None), ("holistic", None), ("factor_when_justified", 2), ("factor_when_justified", 3)]


def check5(cfg):
    c5 = cfg["study2"]["check5"]
    sim = tasks.similarity_matrix(tasks.response_matrix())
    m = c5["margin"]
    patterns, ok = [], 0
    for i in range(c5["n_histories"]):
        target, stages = baselines_study2.scripted_design(sim, np.random.default_rng([c5["seed"], i]),
                                                          cfg["study2"]["baselines"]["scripted_n_candidates"])
        known, rows = [], []
        for stage in stages:
            known = known + stage
            rows.append([learners.mean_cost(l, target, known, cfg, sim, k) for l, k in HYPS])
        rows = np.array(rows)  # stages x hypotheses
        separated = all(np.abs(rows[:, a] - rows[:, b]).max() > m for a, b in itertools.combinations(range(4), 2))
        ok += separated
        patterns.append({"target": target, "stages": stages, "max_sim": float(sim[target, sum(stages, [])].max()),
                         "costs": rows.round(1).tolist(), "all_pairs_separated": bool(separated)})
    rng = np.random.default_rng(c5["seed"])
    sep = {2: 0, 3: 0}
    for _ in range(c5["n_histories"]):
        known = [int(u) for u in rng.choice(64, size=c5["train_size"], replace=False)]
        for k in (2, 3):
            for t in range(64):
                if t in known:
                    continue
                f = learners.mean_cost("factor_when_justified", t, known, cfg, sim, k)
                if abs(f - learners.mean_cost("part_based", t, known, cfg, sim)) > m and \
                        abs(f - learners.mean_cost("holistic", t, known, cfg, sim)) > m:
                    sep[k] += 1
                    break
    mean_costs = np.array([p["costs"] for p in patterns]).mean(axis=0).round(1).tolist()
    out = {"a_share_all_pairs_separated": ok / c5["n_histories"],
           "a_mean_costs_stage_by_hypothesis": mean_costs, "a_hypotheses": [f"{l}{'' if k is None else '_k%d' % k}" for l, k in HYPS],
           "a_median_max_sim": float(np.median([p["max_sim"] for p in patterns])),
           "b_share_histories_with_separating_test": {k: v / c5["n_histories"] for k, v in sep.items()},
           "pass": ok / c5["n_histories"] >= 0.9, "designs": patterns}
    with open(OUT / "check5.json", "w") as f:
        json.dump(out, f, indent=1)
    print({k: v for k, v in out.items() if k != "designs"})


def learner_for(i, ks):
    """Instance i: learners cycle part-based, holistic, factor; the factor learner's k alternates."""
    learner = ["part_based", "holistic", "factor_when_justified"][i % 3]
    k = ks[(i // 3) % len(ks)] if learner == "factor_when_justified" else None
    return learner, k


def one(args):
    cfg, seed, i, name = args
    learner, k = learner_for(i, cfg["study2"]["k_values"])
    env = Environment(learner, seed * 100000 + i, cfg, "study2", k=k)
    baselines_study2.BASELINES[name](env, seed * 100000 + i + 1)
    s = scoring.score(env)
    return {"i": i, "learner": learner, "k": k, "baseline": name, "correct": s["correct"], "brier": s["brier"],
            "design_score": s["design_score"], "verdict": env.verdict["verdict"]}


def run(cfg, seed, budget, n, pool):
    c = json.loads(json.dumps(cfg))
    c["environment"]["budget"] = budget
    rows = pool.map(one, [(c, seed, i, b) for b in baselines_study2.BASELINES for i in range(n)], chunksize=4)
    summ = {}
    for b in baselines_study2.BASELINES:
        r = [x for x in rows if x["baseline"] == b]
        summ[b] = {"accuracy": float(np.mean([x["correct"] for x in r])),
                   "by_learner": {l: float(np.mean([x["correct"] for x in r if x["learner"] == l]))
                                  for l in ("part_based", "holistic", "factor_when_justified")},
                   "brier": float(np.mean([x["brier"] for x in r])),
                   "design_score": float(np.mean([x["design_score"] for x in r]))}
    return summ, rows


def check6(cfg):
    c6 = cfg["study2"]["check6"]
    out = {"grid": {}}
    with Pool() as pool:
        for budget in cfg["study2"]["budget_grid"]:
            s, _ = run(cfg, c6["seed"], budget, c6["n_instances"], pool)
            out["grid"][budget] = s
            print(budget, json.dumps(s), flush=True)
        ok = [b for b in cfg["study2"]["budget_grid"] if out["grid"][b]["scripted"]["accuracy"] >= c6["pass"]["min_scripted_accuracy"]]
        sel = min(ok) if ok else None
        out["selected_budget"] = sel
        if sel is not None:
            s, rows = run(cfg, c6["confirm_seed"], sel, c6["n_instances"], pool)
            out["confirm"] = s
            out["confirm_rows"] = rows
            out["pass"] = bool(s["scripted"]["accuracy"] >= c6["pass"]["min_scripted_accuracy"] and
                               s["random_interleaved"]["accuracy"] <= s["scripted"]["accuracy"] - c6["pass"]["min_gap_to_random"])
            print("confirm", sel, json.dumps(s), "pass", out["pass"])
        else:
            out["pass"] = False
            print("no budget reaches the scripted criterion")
    with open(OUT / "check6.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    cfg = load_config()
    {"check5": check5, "check6": check6}[sys.argv[1]](cfg)
