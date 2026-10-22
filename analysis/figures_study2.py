"""Study 2 figure: Claude beside the baselines by learner, and Claude in the loop vs. the inference-only control
vs. the ideal analysis of Claude's data. Reads results/summary_s2main.json and results/inference_control.json;
writes results/figures/study2.png."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.summarize import wilson

RESULTS = Path(__file__).resolve().parent.parent / "results"
GROUPS = [("all", "All\n(n = 30)"), ("part_based", "Part-based"), ("holistic", "Holistic"),
          ("factor_when_justified", "Factor-when-\njustified")]
EXPS = [("claude", "Claude", "#2a78d6"), ("scripted", "Scripted before/after", "#1baf7a"),
        ("random_interleaved", "Random interleaved", "#eb6834"), ("train_first", "Train-first", "#eda100")]
PANELS = [("accuracy", "accuracy_ci", "Accuracy"), ("design", "design_ci", "Design score (ideal posterior of truth)"),
          ("brier", "brier_ci", "Brier score (lower is better)")]
INF = [("loop", "Claude, in the loop", "#2a78d6"), ("control", "Claude, data table only", "#7b5ea7"),
       ("ideal", "Ideal analysis of Claude's data", "#888888")]


def main():
    summ = json.load(open(RESULTS / "summary_s2main.json"))["summary"]
    control = json.load(open(RESULTS / "inference_control.json"))["runs"]
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#888888", "xtick.color": "#444444", "ytick.color": "#555555"})
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.4), constrained_layout=True)
    off = {e[0]: (i - 1.5) * 0.17 for i, e in enumerate(EXPS)}
    for ax, (key, ci, title) in zip(axes[:3], PANELS):
        for g, (grp, _) in enumerate(GROUPS):
            for name, label, color in EXPS:
                s = summ[f"{grp}/{name}"]
                x = g + off[name]
                ax.plot([x, x], s[ci], color=color, lw=2, solid_capstyle="round")
                ax.plot(x, s[key], "o", ms=8 if name == "claude" else 6, color=color, markeredgecolor="white",
                        markeredgewidth=1.5, label=label if g == 0 else None)
        ax.axvline(0.5, color="#bbbbbb", lw=1, ls="--")
        ax.set_xticks(range(len(GROUPS)), [g[1] for g in GROUPS])
        ax.set_ylim(-0.04, 1.04)
        ax.grid(axis="y", color="#e8e8e8", lw=0.8)
        ax.set_title(title, loc="left", fontsize=10)
    ax = axes[3]
    off2 = {e[0]: (i - 1) * 0.22 for i, e in enumerate(INF)}
    for g, (grp, _) in enumerate(GROUPS):
        runs = [r for r in control if grp == "all" or r["learner"] == grp]
        vals = {"loop": [r["in_loop_correct"] for r in runs], "control": [r["correct"] for r in runs],
                "ideal": [r["ideal_correct"] for r in runs]}
        for name, label, color in INF:
            k, n = sum(vals[name]), len(vals[name])
            x = g + off2[name]
            ax.plot([x, x], wilson(k, n), color=color, lw=2, solid_capstyle="round")
            ax.plot(x, k / n, "o", ms=7, color=color, markeredgecolor="white", markeredgewidth=1.5,
                    label=label if g == 0 else None)
    ax.axvline(0.5, color="#bbbbbb", lw=1, ls="--")
    ax.set_xticks(range(len(GROUPS)), [g[1] for g in GROUPS])
    ax.set_ylim(-0.04, 1.04)
    ax.grid(axis="y", color="#e8e8e8", lw=0.8)
    ax.set_title("Accuracy: design vs. inference", loc="left", fontsize=10)
    h1, l1 = axes[0].get_legend_handles_labels()
    h2, l2 = axes[3].get_legend_handles_labels()
    fig.legend(h1 + h2[1:], l1 + l2[1:], loc="outside lower center", ncol=6, frameon=False)
    fig.suptitle("Study 2: Claude identifying a factor-when-justified learner, beside baselines on the same instances "
                 "(mean, 95% interval; n = 10 per learner)", x=0.01, ha="left", fontsize=11)
    (RESULTS / "figures").mkdir(exist_ok=True)
    fig.savefig(RESULTS / "figures" / "study2.png", dpi=160)


if __name__ == "__main__":
    main()
