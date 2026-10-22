"""Summarize the Study 2 main run: Claude beside the baselines on the same instances, by learner.
Writes results/summary_study2.json and prints a markdown table."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.summarize import boot, wilson
from env.config import load_config

RESULTS = Path(__file__).resolve().parent.parent / "results"
GROUPS = ["all", "part_based", "holistic", "factor_when_justified"]


def main(prefix="s2main"):
    cfg = load_config()
    rng = np.random.default_rng(cfg["summary"]["seed"])
    n_boot = cfg["summary"]["n_bootstrap"]
    records = [json.load(open(f)) for f in sorted(RESULTS.glob(f"{prefix}-*.json"))]
    out, lines = {}, ["| Learner | Experimenter | n | Accuracy [95% CI] | Brier [CI] | Design score [CI] | Ideal analyst on this data |",
                      "|---|---|---|---|---|---|---|"]
    for g in GROUPS:
        recs = [r for r in records if g == "all" or r["learner"] == g]
        if not recs:
            continue
        exps = {"claude": [r["scores"] for r in recs]}
        for name in recs[0]["baselines_same_instance"]:
            exps[name] = [r["baselines_same_instance"][name] for r in recs]
        for name, sc in exps.items():
            n, k = len(sc), sum(s["correct"] for s in sc)
            row = {"n": n, "accuracy": k / n, "accuracy_ci": wilson(k, n),
                   "brier": float(np.mean([s["brier"] for s in sc])), "brier_ci": boot([s["brier"] for s in sc], rng, n_boot),
                   "design": float(np.mean([s["design_score"] for s in sc])),
                   "design_ci": boot([s["design_score"] for s in sc], rng, n_boot),
                   "ideal_accuracy": float(np.mean([s["ideal_correct"] for s in sc]))}
            if name == "claude":
                gaps = [s["inference_gap"] for s in sc if s["inference_gap"] is not None]
                row["inference_gap"] = float(np.mean(gaps))
                row["inference_gap_ci"] = boot(gaps, rng, n_boot)
                row["inference_gap_when_wrong"] = (float(np.mean([s["inference_gap"] for s in sc if not s["correct"] and s["inference_gap"] is not None]))
                                                   if any(not s["correct"] for s in sc) else None)
            out[f"{g}/{name}"] = row
            f = lambda v, ci: f"{v:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]"
            lines.append(f"| {g} | {name} | {n} | {f(row['accuracy'], row['accuracy_ci'])} | {f(row['brier'], row['brier_ci'])} | "
                         f"{f(row['design'], row['design_ci'])} | {row['ideal_accuracy']:.2f} |")
    confusion = {}
    for r in records:
        key = r["learner"] + (f"_k{r['scores']['k']}" if r["scores"].get("k") else "")
        v = (r["verdict"] or {}).get("verdict", "none")
        confusion.setdefault(key, {}).setdefault(v, 0)
        confusion[key][v] += 1
    res = {"summary": out, "confusion": confusion, "n_records": len(records),
           "cost_usd": float(sum(r["claude"]["total_cost_usd"] or 0 for r in records)),
           "verdict_sources": {s: sum(r["claude"].get("verdict_source") == s for r in records) for s in ("submit", "final_message", None)},
           "audit_all_pass": all(r["audit"]["pass"] for r in records)}
    with open(RESULTS / f"summary_{prefix}.json", "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\n".join(lines))
    print("claude inference gap:", {g: (round(out[f'{g}/claude']['inference_gap'], 3), [round(x, 3) for x in out[f'{g}/claude']['inference_gap_ci']])
                                     for g in GROUPS if f"{g}/claude" in out})
    print("confusion", json.dumps(confusion))
    print("cost", round(res["cost_usd"], 2), "sources", res["verdict_sources"], "audit", res["audit_all_pass"], "n", len(records))


if __name__ == "__main__":
    main(*sys.argv[1:])
