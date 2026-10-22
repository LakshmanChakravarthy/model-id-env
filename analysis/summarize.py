"""Summarize the main run: Claude beside the same-instance baselines, per condition and learner.

Writes results/summary.json and prints a markdown table.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env.config import load_config

RESULTS = Path(__file__).resolve().parent.parent / "results"


def wilson(k, n, z=1.96):
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(max(0.0, c - h)), float(min(1.0, c + h))]


def boot(x, rng, n_boot):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return [float("nan"), float("nan")]
    means = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def summarize(scores, rng, n_boot):
    n = len(scores)
    k = sum(s["correct"] for s in scores)
    d = sum(s["has_decisive_pair"] for s in scores)
    return {"n": n, "accuracy": k / n if n else float("nan"), "accuracy_ci": wilson(k, n),
            "brier": float(np.mean([s["brier"] for s in scores])) if n else float("nan"),
            "brier_ci": boot([s["brier"] for s in scores], rng, n_boot),
            "dissociation": float(np.mean([s["dissociation"] for s in scores])) if n else float("nan"),
            "dissociation_ci": boot([s["dissociation"] for s in scores], rng, n_boot),
            "decisive_pair_share": d / n if n else float("nan"), "decisive_pair_ci": wilson(d, n)}


def groups(records):
    out = {}
    for r in records:
        cond = r["condition"]
        keys = [(cond, "all")]
        if cond == "case4":
            keys.append((cond, "holistic" if r["learner"] == "holistic" else "part-based-looking"))
        else:
            keys.append((cond, r["learner"]))
        for key in keys:
            out.setdefault(key, []).append(r)
    return out


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["summary"]["seed"])
    n_boot = cfg["summary"]["n_bootstrap"]
    records = [json.load(open(f)) for f in sorted(RESULTS.glob("main-*.json")) + sorted(RESULTS.glob("case4-*.json"))]
    summary = {}
    lines = ["| Condition | Group | Experimenter | n | Accuracy [95% CI] | Brier [CI] | Dissociation [CI] | Decisive pair [CI] |",
             "|---|---|---|---|---|---|---|---|"]
    for (cond, group), recs in sorted(groups(records).items()):
        experimenters = {"claude": [r["scores"] for r in recs]}
        for name in recs[0]["baselines_same_instance"]:
            experimenters[name] = [r["baselines_same_instance"][name] for r in recs]
        for name, sc in experimenters.items():
            s = summarize(sc, rng, n_boot)
            summary[f"{cond}/{group}/{name}"] = s
            f = lambda v, ci: f"{v:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]"
            lines.append(f"| {cond} | {group} | {name} | {s['n']} | {f(s['accuracy'], s['accuracy_ci'])} | "
                         f"{f(s['brier'], s['brier_ci'])} | {f(s['dissociation'], s['dissociation_ci'])} | "
                         f"{f(s['decisive_pair_share'], s['decisive_pair_ci'])} |")
    verdicts = {}
    for r in records:
        key = f"{r['condition']}/{r['learner']}"
        v = (r["verdict"] or {}).get("verdict", "none")
        verdicts.setdefault(key, {}).setdefault(v, 0)
        verdicts[key][v] += 1
    out = {"summary": summary, "verdict_counts": verdicts,
           "cost_usd": float(sum(r["claude"]["total_cost_usd"] or 0 for r in records)),
           "verdict_sources": {s: sum(r["claude"].get("verdict_source") == s for r in records)
                               for s in ("submit", "final_message", None)},
           "audit_all_pass": all(r["audit"]["pass"] for r in records), "n_records": len(records)}
    with open(RESULTS / "summary.json", "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\n".join(lines))
    print("verdict counts", json.dumps(verdicts))
    print("cost", round(out["cost_usd"], 2), "verdict sources", out["verdict_sources"],
          "audit all pass", out["audit_all_pass"], "records", len(records))


if __name__ == "__main__":
    main()
