"""Study 5 figure: probability on the true account by evidence level, Claude (two instructions) vs. the ideal reader,
per true account. Reads results/study5/main/raw; writes results/figures/study5.png."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.study5_analysis import load
from analysis.summarize import boot

OUT = Path(__file__).resolve().parent.parent / "results" / "figures" / "study5.png"
ACCOUNTS = ["compositional", "conjunctive", "dual-route"]
LEVELS = [1, 2, 3, 4]
LEVEL_LABELS = ["L1\npracticed\nvs. novel", "L2\n+ shared rules,\nrule type", "L3\n+ intrusions", "L4\n+ repetition\nx lag"]
SERIES = [("ideal", "Ideal reader", "#8a8a8a"), ("base", "Claude", "#2a78d6"),
          ("alternatives", "Claude + 'consider each account'", "#1baf7a")]


def main():
    rows = [r for r in load("main") if r["score"] is not None]
    rng = np.random.default_rng(0)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#888888", "xtick.color": "#444444", "ytick.color": "#555555"})
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True, constrained_layout=True)
    for ax, acc in zip(axes, ACCOUNTS):
        for key, label, color in SERIES:
            means, los, his = [], [], []
            for L in LEVELS:
                if key == "ideal":
                    vals = [r["score"]["ideal_p_truth"] for r in rows if r["account"] == acc and r["level"] == L
                            and r["instruction"] == "base"]
                else:
                    vals = [r["score"]["p_truth"] for r in rows if r["account"] == acc and r["level"] == L
                            and r["instruction"] == key]
                means.append(np.mean(vals))
                lo, hi = boot(vals, rng, 5000)
                los.append(lo)
                his.append(hi)
            x = np.array(LEVELS) + {"ideal": -0.08, "base": 0.0, "alternatives": 0.08}[key]
            ax.fill_between(x, los, his, color=color, alpha=0.12, linewidth=0)
            ax.plot(x, means, "-o", color=color, lw=2, ms=6, label=label,
                    markeredgecolor="white", markeredgewidth=1.2)
        ax.axhline(1 / 3, color="#bbbbbb", lw=1, ls="--")
        ax.text(4.3, 1 / 3, "chance", color="#888888", va="center", fontsize=8)
        ax.set_xticks(LEVELS, LEVEL_LABELS)
        ax.set_ylim(0, 1.04)
        ax.set_xlim(0.7, 4.6)
        ax.grid(axis="y", color="#e8e8e8", lw=0.8)
        ax.set_title(f"True account: {acc}", loc="left", fontsize=10)
    axes[0].set_ylabel("Probability on the true account (mean, 95% interval)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="outside lower center", ncol=3, frameon=False)
    fig.suptitle("Study 5: reading simulated C-PRO experiments. Claude's belief rises with evidence, but far less "
                 "than the evidence warrants (8 experiments per account)", x=0.01, ha="left", fontsize=11)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=160)


if __name__ == "__main__":
    main()
