"""Check 4 (case 4, non-identifiability).

(i) The factorized holistic learner's mean cost equals the part-based learner's for every task and
    training set (exact). (ii) The D-optimal design with the aware analysis is >= 0.90 correct.
Writes results/checks/check4.json.
"""
import functools
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import learners, scoring, tasks
from env.config import load_config
from env.environment import Environment
from harness import baselines

OUT_DIR = Path(__file__).resolve().parent.parent / "results" / "checks"
LEARNERS = ["holistic", "holistic", "part_based", "factorized_holistic"]   # half holistic, a quarter each
EXPERIMENTERS = {
    "random": baselines.random_experimenter,
    "dopt": baselines.dopt_experimenter,
    "random_aware": functools.partial(baselines.random_experimenter, analysis="aware"),
    "dopt_aware": functools.partial(baselines.dopt_experimenter, analysis="aware"),
}


def equivalence(cfg):
    c1 = cfg["check1"]
    rng = np.random.default_rng(c1["seed"])
    sim = tasks.similarity_matrix(tasks.response_matrix(cfg["tasks"]["n_features"]))
    max_diff = 0.0
    for _ in range(c1["n_train_sets"]):
        known = [int(k) for k in rng.choice(64, size=c1["train_size"], replace=False)]
        for t in range(64):
            a = learners.mean_cost("part_based", t, known, cfg, sim)
            b = learners.mean_cost("factorized_holistic", t, known, cfg, sim)
            max_diff = max(max_diff, abs(a - b))
    return max_diff


def one_instance(args):
    cfg, seed, i, experimenter = args
    instance_seed = seed * 100000 + i
    env = Environment(LEARNERS[i % 4], instance_seed, cfg, "case4")
    EXPERIMENTERS[experimenter](env, instance_seed + 1)
    return {"i": i, "learner": env.learner, "experimenter": experimenter, **scoring.score(env)}


def main():
    cfg = load_config()
    c4 = cfg["check4"]
    max_diff = equivalence(cfg)
    with Pool() as pool:
        rows = pool.map(one_instance, [(cfg, c4["seed"], i, e) for e in EXPERIMENTERS
                                       for i in range(c4["n_instances"])], chunksize=8)
    summary = {}
    for e in EXPERIMENTERS:
        r = [x for x in rows if x["experimenter"] == e]
        summary[e] = {"accuracy": float(np.mean([x["correct"] for x in r])),
                      "accuracy_by_learner": {l: float(np.mean([x["correct"] for x in r if x["learner"] == l]))
                                              for l in sorted(set(LEARNERS))},
                      "dissociation_mean": float(np.mean([x["dissociation"] for x in r])),
                      "brier_mean": float(np.mean([x["brier"] for x in r])), "n": len(r)}
    passed = bool(max_diff == 0.0 and summary["dopt_aware"]["accuracy"] >= c4["pass"]["min_dopt_aware_accuracy"])
    out = {"config": cfg, "equivalence_max_abs_diff": max_diff, "summary": summary, "pass": passed, "rows": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "check4.json", "w") as f:
        json.dump(out, f, indent=1)
    print("equivalence max |diff|", max_diff)
    for e, s in summary.items():
        print(f"  {e:<13} accuracy {s['accuracy']:.3f}  by learner {s['accuracy_by_learner']}  "
              f"dissociation {s['dissociation_mean']:.2f}  brier {s['brier_mean']:.3f}")
    print("pass", passed)


if __name__ == "__main__":
    main()
