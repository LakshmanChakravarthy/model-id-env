"""Main figure: Claude beside the baselines, by condition and learner group. Reads results/summary.json,
writes results/figures/main.png."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path(__file__).resolve().parent.parent / "results"
GROUPS = [("main", "part_based", "Main\npart-based"), ("main", "holistic", "Main\nholistic"),
          ("case4", "holistic", "Case 4\nholistic"), ("case4", "part-based-looking", "Case 4\npart-based-\nlooking")]
EXPERIMENTERS = [("claude", "Claude", "#2a78d6"), ("random", "Random design", "#eb6834"),
                 ("dopt", "D-optimal design", "#1baf7a"), ("dopt_aware", "D-optimal + aware analysis", "#eda100")]
PANELS = [("accuracy", "accuracy_ci", "Accuracy", "higher is better"),
          ("brier", "brier_ci", "Brier score", "lower is better"),
          ("dissociation", "dissociation_ci", "Dissociation score", "higher is better"),
          ("decisive_pair_share", "decisive_pair_ci", "Runs with a decisive pair", "higher is better")]


def main():
    summary = json.load(open(RESULTS / "summary.json"))["summary"]
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#888888", "axes.labelcolor": "#333333",
                         "xtick.color": "#444444", "ytick.color": "#555555"})
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), constrained_layout=True)
    offsets = {e[0]: (i - 1.5) * 0.17 for i, e in enumerate(EXPERIMENTERS)}
    for ax, (key, ci_key, title, note) in zip(axes, PANELS):
        for g, (cond, group, _) in enumerate(GROUPS):
            for name, label, color in EXPERIMENTERS:
                s = summary.get(f"{cond}/{group}/{name}")
                if s is None:
                    continue
                x, y = g + offsets[name], s[key]
                lo, hi = s[ci_key]
                ax.plot([x, x], [lo, hi], color=color, lw=2, solid_capstyle="round")
                ax.plot(x, y, "o", ms=8 if name == "claude" else 6, color=color,
                        markeredgecolor="white", markeredgewidth=1.5, label=label if g == 3 or name != "dopt_aware" else None)
        ax.axvline(1.5, color="#bbbbbb", lw=1, ls="--")
        ax.set_xticks(range(len(GROUPS)), [g[2] for g in GROUPS])
        ax.set_ylim(-0.04, 1.04)
        ax.grid(axis="y", color="#e8e8e8", lw=0.8)
        ax.set_title(f"{title}  ({note})", loc="left", fontsize=10)
    handles, labels = axes[0].get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    fig.legend(uniq.values(), uniq.keys(), loc="outside lower center", ncol=4, frameon=False)
    fig.suptitle("Claude as experimenter, beside baselines on the same instances (mean, 95% interval; n = 10 per group)",
                 x=0.01, ha="left", fontsize=11)
    (RESULTS / "figures").mkdir(parents=True, exist_ok=True)
    fig.savefig(RESULTS / "figures" / "main.png", dpi=160)


if __name__ == "__main__":
    main()
