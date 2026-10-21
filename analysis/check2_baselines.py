"""Check 2: the oracle is near 100% correct and the random baseline is clearly lower.

Usage:
  python analysis/check2_baselines.py main      # current config, seed check2.seed
  python analysis/check2_baselines.py grid      # declared tuning grid, seed check2.seed
  python analysis/check2_baselines.py confirm NOISE_SD BUDGET C_SEL   # selected setting, check2.confirm_seed
  python analysis/check2_baselines.py final     # current config, check2.final_seed (Day 2b criterion)
Writes results/checks/check2_<mode>.json.
"""
import copy
import functools
import itertools
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.check1_dissociation import table_for_known
from env import scoring, tasks
from env.config import load_config
from env.environment import Environment
from harness import baselines

OUT_DIR = Path(__file__).resolve().parent.parent / "results" / "checks"
LEARNERS = ["part_based", "holistic"]
EXPERIMENTERS = {"random": baselines.random_experimenter, "oracle": baselines.oracle_experimenter,
                 "random_naive": functools.partial(baselines.random_experimenter, analysis="naive"),
                 "oracle_naive": functools.partial(baselines.oracle_experimenter, analysis="naive")}


def matched_c0(cfg):
    """c0 that equalizes mean costs over the check-1 distribution (same procedure as check 1)."""
    c1 = cfg["check1"]
    rng = np.random.default_rng(c1["seed"])
    sim = tasks.similarity_matrix(tasks.response_matrix(cfg["tasks"]["n_features"]))
    rows = []
    for _ in range(c1["n_train_sets"]):
        rows += table_for_known([int(k) for k in rng.choice(64, size=c1["train_size"], replace=False)], cfg, sim)
    m = cfg["similarity"]["measure"]
    mean_pb = np.mean([r["part_based"] for r in rows])
    s = np.array([r[f"sim_{m}"] for r in rows])
    return float((mean_pb - cfg["holistic"]["base"]) / np.mean((1 - s) ** cfg["holistic"]["alpha"]))


def with_setting(cfg, noise_sd, budget, c_sel):
    c = copy.deepcopy(cfg)
    c["noise"]["sd"], c["environment"]["budget"], c["part_based"]["c_sel"] = noise_sd, budget, c_sel
    c["holistic"]["c0"] = round(matched_c0(c), 1)
    return c


def one_instance(args):
    cfg, seed, i, experimenter = args
    instance_seed = seed * 100000 + i
    env = Environment(LEARNERS[i % 2], instance_seed, cfg)
    EXPERIMENTERS[experimenter](env, instance_seed + 1)
    return {"i": i, "learner": env.learner, "experimenter": experimenter, **scoring.score(env)}


def run_setting(cfg, seed, n, pool):
    jobs = [(cfg, seed, i, e) for e in EXPERIMENTERS for i in range(n)]
    rows = pool.map(one_instance, jobs, chunksize=8)
    summary = {}
    for e in EXPERIMENTERS:
        r = [x for x in rows if x["experimenter"] == e]
        summary[e] = {"accuracy": float(np.mean([x["correct"] for x in r])),
                      "accuracy_by_learner": {l: float(np.mean([x["correct"] for x in r if x["learner"] == l]))
                                              for l in LEARNERS},
                      "dissociation_mean": float(np.mean([x["dissociation"] for x in r])),
                      "brier_mean": float(np.mean([x["brier"] for x in r])),
                      "n": len(r)}
    crit = cfg["check2"]["pass"]
    acc_o, acc_r = summary["oracle"]["accuracy"], summary["random"]["accuracy"]
    summary["gap"] = acc_o - acc_r
    summary["dissociation_gap"] = summary["oracle"]["dissociation_mean"] - summary["random"]["dissociation_mean"]
    if "min_dissociation_gap" in crit:   # Day 2b criterion
        summary["pass"] = bool(acc_o >= crit["min_oracle_accuracy"]
                               and summary["dissociation_gap"] >= crit["min_dissociation_gap"])
    else:                                # Day 2 criterion
        summary["pass"] = bool(acc_o >= crit["min_oracle_accuracy"] and summary["gap"] >= crit["min_gap"])
    return summary, rows


def line(setting, s):
    out = [f"{setting}  pass {s['pass']}"]
    for e in EXPERIMENTERS:
        out.append(f"  {e:<13} accuracy {s[e]['accuracy']:.3f}  dissociation {s[e]['dissociation_mean']:.2f}  "
                   f"brier {s[e]['brier_mean']:.3f}  by learner {s[e]['accuracy_by_learner']}")
    return "\n".join(out)


def main(mode="main", *setting):
    cfg = load_config()
    c2 = cfg["check2"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with Pool() as pool:
        if mode == "main":
            s, rows = run_setting(cfg, c2["seed"], c2["n_instances"], pool)
            out = {"mode": mode, "config": cfg, "summary": s, "rows": rows}
            print(line("current config", s))
        elif mode == "final":
            s, rows = run_setting(cfg, c2["final_seed"], c2["n_instances"], pool)
            out = {"mode": mode, "config": cfg, "summary": s, "rows": rows}
            print(line("current config, final seed", s))
        elif mode == "grid":
            g = c2["tuning_grid"]
            out = {"mode": mode, "seed": c2["seed"], "settings": []}
            for sd, budget, c_sel in itertools.product(g["noise_sd"], g["budget"], g["c_sel"]):
                c = with_setting(cfg, sd, budget, c_sel)
                s, _ = run_setting(c, c2["seed"], c2["n_instances"], pool)
                out["settings"].append({"noise_sd": sd, "budget": budget, "c_sel": c_sel,
                                        "c0": c["holistic"]["c0"], "summary": s})
                print(line(f"sd={sd:>2} budget={budget} c_sel={c_sel} c0={c['holistic']['c0']}", s), flush=True)
            ok = [x for x in out["settings"] if x["summary"]["oracle"]["accuracy"] >= c2["pass"]["min_oracle_accuracy"]]
            best = max(ok, key=lambda x: (round(x["summary"]["gap"], 6), x["budget"])) if ok else None
            out["selected"] = {k: best[k] for k in ("noise_sd", "budget", "c_sel", "c0")} if best else None
            print("selected", out["selected"])
        elif mode == "confirm":
            sd, budget, c_sel = float(setting[0]), int(setting[1]), float(setting[2])
            c = with_setting(cfg, sd, budget, c_sel)
            s, rows = run_setting(c, c2["confirm_seed"], c2["n_instances"], pool)
            out = {"mode": mode, "config": c, "summary": s, "rows": rows}
            print(line(f"confirm sd={sd} budget={budget} c_sel={c_sel} c0={c['holistic']['c0']}", s))
        else:
            raise ValueError(mode)
    with open(OUT_DIR / f"check2_{mode}.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
