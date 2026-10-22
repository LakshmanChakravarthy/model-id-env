"""Study 4 analysis, as preregistered (docs/study4_preregistration.md, sections 6-7).

Usage:
  python analysis/study4_analysis.py analyse [main|pilot]   # tables, H1-H4 with Holm, secondary measures
  python analysis/study4_analysis.py sample                  # draw the 40-response validation sample for hand-coding
  python analysis/study4_analysis.py kappa                   # grader vs. user agreement, once the user's codes exist
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.summarize import wilson

R4 = Path(__file__).resolve().parent.parent / "results" / "study4"
VALID = R4 / "validation"
CATEGORIES = ["none", "categorical", "ordinal", "polarity", "other"]


def load(mode):
    rows = []
    for f in sorted((R4 / mode / "raw").glob("*.json")):
        r = json.load(open(f))
        g = R4 / mode / "grades" / f.name
        r["grade"] = json.load(open(g))["code"] if g.exists() else None
        r.pop("prompt", None)
        rows.append(r)
    return rows


def mcnemar_one_sided(pairs):
    """pairs: list of (treatment, control) binary outcomes. H1: treatment > control."""
    b = sum(1 for t, c in pairs if t == 1 and c == 0)
    c = sum(1 for t, c in pairs if t == 0 and c == 1)
    p = binomtest(b, b + c, 0.5, alternative="greater").pvalue if b + c else 1.0
    return {"n_pairs": len(pairs), "treatment_only": b, "control_only": c, "p": float(p)}


def mcnemar_two_sided(pairs):
    b = sum(1 for t, c in pairs if t == 1 and c == 0)
    c = sum(1 for t, c in pairs if t == 0 and c == 1)
    p = binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
    return {"n_pairs": len(pairs), "first_only": b, "second_only": c, "p": float(p)}


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    adj, running = {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, ps[k] * (len(ps) - i)))
        adj[k] = running
    return adj


def index(rows):
    return {(r["id"], r["format"], r["prompt_variant"]): r for r in rows}


def prop(rr, key="R"):
    v = [r[key] for r in rr if r[key] is not None]
    return {"k": int(sum(v)), "n": len(v), "p": (sum(v) / len(v)) if v else None, "ci": wilson(int(sum(v)), len(v))}


def visible(r):
    return r["cell"] != "irregular" and not (r["type"] == "ordinal" and r["format"] == "colours")


def analyse(mode):
    rows = [r for r in load(mode) if r["R"] is not None]
    n_unparsed = len(load(mode)) - len(rows)
    ix = index(rows)
    res = {"n_responses": len(rows), "n_unparsed": n_unparsed,
           "cost_usd": float(sum(r["cost_usd"] or 0 for r in load(mode)))}

    # H1: categorical regular, colours vs digits, paired by instance and prompt.
    h1 = [(ix[(i, "colours", pv)]["R"], ix[(i, "digits", pv)]["R"])
          for (i, f, pv), r in ix.items() if f == "colours" and r["type"] == "categorical" and r["cell"] != "irregular"
          and (i, "digits", pv) in ix]
    # H2: visible cells, pattern vs base, paired by instance and format.
    h2 = [(ix[(i, f, "pattern")]["R"], ix[(i, f, "base")]["R"])
          for (i, f, pv), r in ix.items() if pv == "pattern" and visible(r) and (i, f, "base") in ix]
    # H3: visible cells with R = 1: ideal - confidence > 0.
    d3 = [r["ideal_p_modal"] - r["confidence"] for r in rows if visible(r) and r["R"] == 1 and r["confidence"] is not None]
    h3p = float(wilcoxon(d3, alternative="greater").pvalue) if len(d3) > 1 and any(d3) else 1.0
    # H4: irregular cells, confident claims.
    irr = [r for r in rows if r["cell"] == "irregular"]
    k4 = sum(1 for r in irr if r["determined"] is True or (r["confidence"] is not None and r["confidence"] >= 0.7))
    h4p = float(binomtest(k4, len(irr), 0.15, alternative="less").pvalue) if irr else 1.0
    tests = {"H1": mcnemar_one_sided(h1), "H2": mcnemar_one_sided(h2),
             "H3": {"n": len(d3), "mean_gap": float(np.mean(d3)) if d3 else None, "p": h3p},
             "H4": {"k": k4, "n": len(irr), "rate": k4 / len(irr) if irr else None, "p": h4p}}
    adj = holm({h: t["p"] for h, t in tests.items()})
    for h in tests:
        tests[h]["p_holm"] = adj[h]
        tests[h]["supported"] = adj[h] < 0.05
    res["confirmatory"] = tests

    # Secondary (a)-(f).
    sec = {}
    pol = [(ix[(i, "digits", pv)]["R"], ix[(i, "colours", pv)]["R"])
           for (i, f, pv), r in ix.items() if f == "digits" and r["type"] == "polarity" and r["cell"] != "irregular"
           and (i, "colours", pv) in ix]
    sec["a_polarity_format_digits_vs_colours"] = mcnemar_two_sided(pol)
    od = [r for r in rows if r["type"] == "ordinal" and r["cell"] != "irregular" and r["format"] == "digits"]
    sec["b_ordinal_digits_R"] = {**prop(od), "p_vs_0.5": float(binomtest(int(sum(r["R"] for r in od)), len(od), 0.5).pvalue) if od else None}
    sec["c_ordinal_colours_R"] = prop([r for r in rows if r["type"] == "ordinal" and r["cell"] != "irregular" and r["format"] == "colours"])
    sec["d_confidence_by_band"] = {
        f"{t}/{c}/{pv}": {"mean_conf": float(np.mean([r["confidence"] for r in rr if r["confidence"] is not None])),
                          "mean_ideal": float(np.mean([r["ideal_p_modal"] for r in rr])), "n": len(rr)}
        for t in ("categorical", "ordinal", "polarity") for c in ("high", "moderate", "irregular") for pv in ("base", "pattern")
        for rr in [[r for r in rows if visible(r) or c == "irregular"
                    if r["type"] == t and r["cell"] == c and r["prompt_variant"] == pv]] if rr}
    graded = [r for r in irr if r["grade"]]
    sec["e_irregular_stated_regularity_by_format"] = {
        f: {"any": prop([{"R": int(r["grade"]["regularity_stated"] not in ("none", None))} for r in graded if r["format"] == f]),
            "ordinal": prop([{"R": int(r["grade"]["regularity_stated"] == "ordinal")} for r in graded if r["format"] == f])}
        for f in ("digits", "colours")}
    sec["f_R_table"] = {f"{t}/{c}/{f}/{pv}": prop([r for r in rows if r["type"] == t and r["cell"] == c and r["format"] == f
                                                  and r["prompt_variant"] == pv])
                        for t in ("categorical", "ordinal", "polarity") for c in ("high", "moderate", "irregular")
                        for f in ("digits", "colours") for pv in ("base", "pattern")}
    sec["coded_stated_regularity_regular_cells"] = {
        f"{t}/{f}/{pv}": {cat: sum(1 for r in rows if r["grade"] and r["type"] == t and r["cell"] != "irregular"
                                   and r["format"] == f and r["prompt_variant"] == pv
                                   and r["grade"]["regularity_stated"] == cat) for cat in CATEGORIES}
        for t in ("categorical", "ordinal", "polarity") for f in ("digits", "colours") for pv in ("base", "pattern")}
    # (g) added 2026-10-22 before main results (see preregistration section 10): H3 restricted to runs where the
    # grader codes regularity_used = true, so that answers picked by chance at 0.5 do not count as under-trust.
    dg = [r["ideal_p_modal"] - r["confidence"] for r in rows if visible(r) and r["R"] == 1 and r["confidence"] is not None
          and r["grade"] and r["grade"].get("regularity_used") is True]
    sec["g_H3_regularity_used_only"] = {"n": len(dg), "mean_gap": float(np.mean(dg)) if dg else None,
                                        "p_one_sided": float(wilcoxon(dg, alternative="greater").pvalue)
                                        if len(dg) > 1 and any(dg) else None}
    res["secondary"] = sec
    out = R4 / mode / "analysis.json"
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({"n": res["n_responses"], "unparsed": n_unparsed, "cost": round(res["cost_usd"], 2)}))
    for h, t in tests.items():
        print(h, json.dumps(t))
    for k in ("a_polarity_format_digits_vs_colours", "b_ordinal_digits_R", "c_ordinal_colours_R",
              "e_irregular_stated_regularity_by_format", "g_H3_regularity_used_only"):
        print(k, json.dumps(sec[k]))


def sample():
    """40 responses, random, stratified by type x prompt (about 7 each), seed 4040; blind to codes and condition."""
    rows = load("main")
    expected = 4 * len(json.load(open(R4 / "main" / "instances.json"))) if (R4 / "main" / "instances.json").exists() else None
    if expected is None or len(rows) < expected:
        sys.exit(f"The main run is not complete ({len(rows)} of {expected or 576} responses). "
                 "Draw the validation sample after it finishes, so that the sample is not biased toward early runs.")
    rng = np.random.default_rng(4040)
    picked = []
    strata = [(t, pv) for t in ("categorical", "ordinal", "polarity") for pv in ("base", "pattern")]
    quota = {s: 7 for s in strata}
    quota[strata[0]] = quota[strata[1]] = 6                      # 6 + 6 + 7 * 4 = 40
    for s in strata:
        pool = [r for r in rows if (r["type"], r["prompt_variant"]) == s and r["text"]]
        for j in rng.choice(len(pool), size=quota[s], replace=False):
            picked.append(pool[int(j)])
    order = rng.permutation(len(picked))
    VALID.mkdir(parents=True, exist_ok=True)
    key = {f"V{n + 1:02d}": picked[int(j)]["id"] + "__" + picked[int(j)]["format"] + "__" + picked[int(j)]["prompt_variant"]
           for n, j in enumerate(order)}
    json.dump(key, open(VALID / "key_do_not_open_before_coding.json", "w"), indent=1)
    lines = ["# Study 4 grader validation: hand-coding sheet", "",
             "For each response, code three things (the same rubric the grader used):", "",
             "- **regularity_stated**: none / categorical / ordinal / polarity / other. Categorical: the buttons split into "
             "two groups, one always used for true and the other for false. Ordinal: an order relation between buttons "
             "holds across components (for example, true is always higher). Polarity: all rules share a property, such as "
             "all being false when neither bit is 1. Other: any other cross-component pattern (for example, the order in "
             "which labels or rules are listed). None: no cross-component regularity is stated; saying that none was found "
             "counts as none. If several, pick the one the response relies on most.",
             "- **regularity_used**: true if the response uses a stated regularity to prefer one assignment or answer.",
             "- **alternatives_considered**: true if it considers at least two assignments that fit the examples.", "",
             "Enter your codes in `results/study4/validation/user_codes.json` (template provided). Please do not open the "
             "key file or the grader codes before coding.", ""]
    template = {}
    for vid in key:
        r = next(x for x in picked if x["id"] + "__" + x["format"] + "__" + x["prompt_variant"] == key[vid])
        lines += [f"## {vid}", "", r["text"], "", "---", ""]
        template[vid] = {"regularity_stated": "", "regularity_used": None, "alternatives_considered": None}
    open(VALID / "coding_sheet.md", "w").write("\n".join(lines))
    json.dump(template, open(VALID / "user_codes.json", "w"), indent=1)
    print("wrote", VALID / "coding_sheet.md", "and the template", VALID / "user_codes.json")


def kappa():
    key = json.load(open(VALID / "key_do_not_open_before_coding.json"))
    user = json.load(open(VALID / "user_codes.json"))
    pairs = []
    for vid, rid in key.items():
        g = json.load(open(R4 / "main" / "grades" / f"{rid}.json"))["code"]
        u = user[vid]
        if g and u.get("regularity_stated"):
            pairs.append((u["regularity_stated"], g["regularity_stated"]))
    def k(pairs, cats):
        n = len(pairs)
        po = sum(a == b for a, b in pairs) / n
        pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
        return (po - pe) / (1 - pe) if pe < 1 else 1.0
    binary = [("type" if a != "none" else "none", "type" if b != "none" else "none") for a, b in pairs]
    res = {"n": len(pairs), "kappa_type_vs_none": k(binary, ["type", "none"]),
           "kappa_five_categories": k(pairs, CATEGORIES), "agreement_five": sum(a == b for a, b in pairs) / len(pairs),
           "reliable": k(binary, ["type", "none"]) >= 0.6}
    json.dump(res, open(VALID / "kappa.json", "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "analyse":
        analyse(sys.argv[2] if len(sys.argv) > 2 else "main")
    elif cmd == "sample":
        sample()
    else:
        kappa()
