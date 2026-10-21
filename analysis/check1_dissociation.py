"""Check 1: does a dissociation between shared parts and overall similarity exist?

For random training sets K, compute for every test task T not in K: new parts, similarity
(max and kernel), and the noise-free cost of both learners. Report the confound
(corr(new_parts, similarity)), the c0 that matches the two learners' mean costs, and the
number of disagreeing pairs. Writes results/checks/check1.json and check1.png.
"""
import itertools
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import learners, tasks
from env.config import load_config

OUT_DIR = Path(__file__).resolve().parent.parent / "results" / "checks"
COLORS = {"part_based": "#2a78d6", "holistic": "#eb6834"}
LABELS = {"part_based": "Part-based", "holistic": "Holistic"}
MEASURES = ["max", "kernel"]


def table_for_known(known, cfg, sim):
    """One row per test task T not in K."""
    rows = []
    for t in range(64):
        if t in known:
            continue
        row = {"t": t, "new_parts": tasks.new_parts(t, known),
               "part_based": learners.mean_cost("part_based", t, known, cfg, sim)}
        for m in MEASURES:
            c = {**cfg, "similarity": {**cfg["similarity"], "measure": m}}
            row[f"sim_{m}"] = tasks.similarity_to_known(t, known, sim, m, cfg["similarity"]["kernel_tau"])
            row[f"holistic_{m}"] = learners.mean_cost("holistic", t, known, c, sim)
        rows.append(row)
    return rows


def disagreeing_pairs(pb, ho, margin):
    """Pairs (A, B) where part-based says A cheaper by > margin and holistic says B cheaper by > margin."""
    n = 0
    for a, b in itertools.permutations(range(len(pb)), 2):
        if pb[b] - pb[a] > margin and ho[a] - ho[b] > margin:
            n += 1
    return n


def safe_corr(x, y):
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main(config_name="default"):
    cfg = load_config(config_name)
    c1 = cfg["check1"]
    rng = np.random.default_rng(c1["seed"])
    sim = tasks.similarity_matrix(tasks.response_matrix(cfg["tasks"]["n_features"]))
    margin = c1["margin_in_sd"] * cfg["noise"]["sd"]

    all_rows, per_k = [], []
    for _ in range(c1["n_train_sets"]):
        known = [int(k) for k in rng.choice(64, size=c1["train_size"], replace=False)]
        rows = table_for_known(known, cfg, sim)
        all_rows += rows
        newp = np.array([r["new_parts"] for r in rows])
        pb = np.array([r["part_based"] for r in rows])
        entry = {"known": known}
        for m in MEASURES:
            s = np.array([r[f"sim_{m}"] for r in rows])
            ho = np.array([r[f"holistic_{m}"] for r in rows])
            entry[f"corr_newparts_sim_{m}"] = safe_corr(newp, s)
            entry[f"corr_costs_{m}"] = safe_corr(pb, ho)
            entry[f"disagreeing_pairs_{m}"] = disagreeing_pairs(pb, ho, margin)
        per_k.append(entry)

    hp = cfg["holistic"]
    mean_pb = np.mean([r["part_based"] for r in all_rows])
    summary = {"config": cfg, "mean_cost_part_based": float(mean_pb)}
    for m in MEASURES:
        s = np.array([r[f"sim_{m}"] for r in all_rows])
        summary[f"mean_cost_holistic_{m}"] = float(np.mean([r[f"holistic_{m}"] for r in all_rows]))
        summary[f"matched_c0_{m}"] = float((mean_pb - hp["base"]) / np.mean((1 - s) ** hp["alpha"]))
        corrs = np.array([e[f"corr_newparts_sim_{m}"] for e in per_k])
        pairs = np.array([e[f"disagreeing_pairs_{m}"] for e in per_k])
        summary[m] = {
            "corr_newparts_sim_pooled": safe_corr([r["new_parts"] for r in all_rows], s),
            "corr_newparts_sim_per_k_median": float(np.nanmedian(corrs)),
            "corr_newparts_sim_per_k_range": [float(np.nanmin(corrs)), float(np.nanmax(corrs))],
            "n_k_with_undefined_corr": int(np.isnan(corrs).sum()),
            "corr_learner_costs_per_k_median": float(np.nanmedian([e[f"corr_costs_{m}"] for e in per_k])),
            "disagreeing_pairs_per_k_min": int(pairs.min()),
            "disagreeing_pairs_per_k_median": float(np.median(pairs)),
            "n_k_with_disagreement": int((pairs > 0).sum()),
            "n_k": len(per_k),
            "pass": bool((pairs > 0).all()),
        }
    summary["per_k"] = per_k

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "check1.json", "w") as f:
        json.dump(summary, f, indent=1)
    plot(all_rows, per_k, cfg, OUT_DIR / "check1.png")
    for m in MEASURES:
        print(m, json.dumps(summary[m]))
    print("mean cost part-based", round(mean_pb, 2),
          {m: round(summary[f"mean_cost_holistic_{m}"], 2) for m in MEASURES},
          "matched c0", {m: round(summary[f"matched_c0_{m}"], 2) for m in MEASURES})


def plot(rows, per_k, cfg, path):
    m = cfg["similarity"]["measure"]
    newp = np.array([r["new_parts"] for r in rows])
    s = np.round(np.array([r[f"sim_{m}"] for r in rows]), 3)
    costs = {"part_based": np.array([r["part_based"] for r in rows]),
             "holistic": np.array([r[f"holistic_{m}"] for r in rows])}

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#888888", "axes.labelcolor": "#333333",
                         "xtick.color": "#555555", "ytick.color": "#555555"})
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), constrained_layout=True)

    for ax, x, xlabel in [(axes[0], newp, "new parts"), (axes[1], s, f"similarity to known ({m})")]:
        xs = np.unique(x)
        for learner, c in costs.items():
            mean = [c[x == v].mean() for v in xs]
            lo = [np.percentile(c[x == v], 10) for v in xs]
            hi = [np.percentile(c[x == v], 90) for v in xs]
            ax.fill_between(xs, lo, hi, color=COLORS[learner], alpha=0.15, linewidth=0)
            ax.plot(xs, mean, "-o", color=COLORS[learner], lw=2, ms=6, label=LABELS[learner])
        ax.set_xlabel(xlabel)
        ax.set_ylabel("mean examples to criterion")
        ax.grid(axis="y", color="#e5e5e5", lw=0.8)
    axes[0].legend(frameon=False)
    axes[0].set_title("Cost vs new parts (mean, 10-90%)", loc="left")
    axes[1].set_title("Cost vs similarity (mean, 10-90%)", loc="left")

    sims = np.unique(s)
    counts = np.array([[np.sum((newp == p) & (s == v)) for v in sims] for p in range(4)])
    im = axes[2].imshow(counts, cmap="Blues", aspect="auto", origin="lower")
    for (i, j), n in np.ndenumerate(counts):
        if n:
            axes[2].text(j, i, n, ha="center", va="center", fontsize=8,
                         color="white" if n > counts.max() / 2 else "#333333")
    axes[2].set_xticks(range(len(sims)), [f"{v:g}" for v in sims])
    axes[2].set_yticks(range(4))
    axes[2].set_xlabel(f"similarity to known ({m})")
    axes[2].set_ylabel("new parts")
    axes[2].set_title("The confound: (K, T) counts", loc="left")

    corrs = np.array([e[f"corr_newparts_sim_{m}"] for e in per_k])
    axes[3].hist(corrs[~np.isnan(corrs)], bins=20, color=COLORS["part_based"], edgecolor="white")
    axes[3].set_xlabel("corr(new parts, similarity) within one K")
    axes[3].set_ylabel("number of training sets K")
    axes[3].set_title(f"Confound per K (n = {len(per_k)}, |K| = {cfg['check1']['train_size']})", loc="left")
    fig.savefig(path, dpi=150)


if __name__ == "__main__":
    main(*sys.argv[1:])
