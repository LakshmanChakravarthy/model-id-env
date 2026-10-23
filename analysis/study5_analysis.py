"""Study 5 analysis, as preregistered (docs/study5_preregistration.md, sections 4-5).
Usage: python analysis/study5_analysis.py [main|pilot]"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.summarize import boot, wilson
from analysis.study4_analysis import holm

R5 = Path(__file__).resolve().parent.parent / "results" / "study5"


def load(mode):
    rows = []
    for f in sorted((R5 / mode / "raw").glob("*.json")):
        r = json.load(open(f))
        r.pop("prompt", None)
        rows.append(r)
    return rows


def wil(x):
    x = [v for v in x if v is not None]
    if len(x) < 2 or not any(x):
        return {"n": len(x), "mean": float(np.mean(x)) if x else None, "p": 1.0}
    return {"n": len(x), "mean": float(np.mean(x)), "p": float(wilcoxon(x, alternative="greater").pvalue)}


def main(mode="main"):
    rows = load(mode)
    ok = [r for r in rows if r["score"] is not None]
    ix = {(r["id"], r["level"], r["instruction"]): r for r in ok}
    rng = np.random.default_rng(0)
    res = {"n_calls": len(rows), "n_unparsed": len(rows) - len(ok),
           "cost_usd": float(sum(r["cost_usd"] or 0 for r in rows))}
    ids = sorted({r["id"] for r in ok})
    h1a = [ix[(i, 4, ins)]["score"]["p_truth"] - ix[(i, 1, ins)]["score"]["p_truth"]
           for i in ids for ins in ("base", "alternatives") if (i, 4, ins) in ix and (i, 1, ins) in ix]
    h1b = [(ix[(i, 4, ins)]["score"]["ideal_p_truth"] - ix[(i, 1, ins)]["score"]["ideal_p_truth"])
           - (ix[(i, 4, ins)]["score"]["p_truth"] - ix[(i, 1, ins)]["score"]["p_truth"])
           for i in ids for ins in ("base", "alternatives") if (i, 4, ins) in ix and (i, 1, ins) in ix]
    h2 = [r["score"]["overclaim_vs_ideal"] for r in ok if r["level"] in (1, 2)]
    h3 = [ix[(i, L, "base")]["score"]["overclaim_vs_ideal"] - ix[(i, L, "alternatives")]["score"]["overclaim_vs_ideal"]
          for i in ids for L in (1, 2) if (i, L, "base") in ix and (i, L, "alternatives") in ix]
    h4 = [r["answer"]["probabilities_normalised"]["compositional"] - r["ideal"]["compositional"]
          for r in ok if r["level"] == 2 and r["account"] != "compositional"]
    tests = {"H1a": wil(h1a), "H1b": wil(h1b), "H2": wil(h2), "H3": wil(h3), "H4": wil(h4)}
    adj = holm({h: t["p"] for h, t in tests.items()})
    for h in tests:
        tests[h]["p_holm"] = adj[h]
        tests[h]["supported"] = adj[h] < 0.05
    res["confirmatory"] = tests
    sec = {}
    for L in (1, 2, 3, 4):
        for ins in ("base", "alternatives"):
            rr = [r for r in ok if r["level"] == L and r["instruction"] == ins]
            k = sum(r["score"]["top_correct"] for r in rr)
            sec[f"L{L}/{ins}"] = {
                "n": len(rr), "top_correct": k / len(rr) if rr else None, "top_correct_ci": wilson(k, len(rr)),
                "ideal_top_correct": float(np.mean([r["score"]["ideal_top_correct"] for r in rr])) if rr else None,
                "p_truth": float(np.mean([r["score"]["p_truth"] for r in rr])) if rr else None,
                "p_truth_ci": boot([r["score"]["p_truth"] for r in rr], rng, 10000),
                "ideal_p_truth": float(np.mean([r["score"]["ideal_p_truth"] for r in rr])) if rr else None,
                "brier": float(np.mean([r["score"]["brier"] for r in rr])) if rr else None,
                "ideal_brier": float(np.mean([r["score"]["ideal_brier"] for r in rr])) if rr else None,
                "overclaim": float(np.mean([r["score"]["overclaim_vs_ideal"] for r in rr])) if rr else None,
                "by_account": {a: {"top_correct": float(np.mean([r["score"]["top_correct"] for r in rr if r["account"] == a])),
                                   "p_truth": float(np.mean([r["score"]["p_truth"] for r in rr if r["account"] == a])),
                                   "ideal_p_truth": float(np.mean([r["score"]["ideal_p_truth"] for r in rr if r["account"] == a]))}
                               for a in ("compositional", "conjunctive", "dual-route") if any(r["account"] == a for r in rr)}}
    res["secondary"] = sec
    json.dump(res, open(R5 / mode / "analysis.json", "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("n_calls", "n_unparsed", "cost_usd")}))
    for h, t in tests.items():
        print(h, json.dumps(t))
    for k, v in sec.items():
        print(k, f"top {v['top_correct']:.2f} (ideal {v['ideal_top_correct']:.2f}) | p_truth {v['p_truth']:.2f} "
                 f"(ideal {v['ideal_p_truth']:.2f}) | Brier {v['brier']:.2f} (ideal {v['ideal_brier']:.2f}) | "
                 f"overclaim {v['overclaim']:+.2f} | " + ", ".join(f"{a}: {x['p_truth']:.2f}/{x['ideal_p_truth']:.2f}"
                                                                 for a, x in v["by_account"].items()))


if __name__ == "__main__":
    main(*sys.argv[1:])
