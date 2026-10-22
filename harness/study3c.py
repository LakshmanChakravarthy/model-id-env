"""Study 3c: can Claude infer an overhypothesis (a TRUE class and a FALSE class of buttons, shared by every Z component)
from data, and use it to resolve compositions that are ambiguous without it? Writes results/study3c.json."""
import json
import math
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env.config import load_config
from harness import study3b as s3b

SPLITS = [({0, 3}, {1, 2}), ({0, 1}, {2, 3}), ({0, 2}, {1, 3})]
CLASS_DOMAINS = [[(f, t) for f in sorted(a) for t in sorted(b)] for s in SPLITS for a, b in (s, s[::-1])]


def crosses(pair, split):
    a, _ = split
    return (pair[0] in a) != (pair[1] in a)


def fits_some_split(pairs):
    return any(all(crosses(p, s) for p in pairs) for s in SPLITS)


# tasks: (l, f, zi); zi indexes the world's list of (FALSE button, TRUE button) pairs
def slots(task):
    return [("X", task[0]), ("Y", task[1]), ("Z", task[2])]


def out(task, world, idx):
    return s3b.flat_out(task[0], task[1], world[task[2]], idx)


def out_under(task, assign, idx):
    return s3b.flat_out(assign[("X", task[0])], assign[("Y", task[1])], assign[("Z", task[2])], idx)


def consistent(known, examples, world, z_domain):
    labels = sorted({s for k in known for s in slots(k)})
    domains = {"X": list(range(4)), "Y": list(range(4)), "Z": z_domain}
    targets = [out(k, world, np.array(ex)) for k, ex in zip(known, examples)]
    need = [set(slots(k)) for k in known]
    order = sorted(labels, key=lambda s: -sum(s in n for n in need))
    sols = []

    def rec(i, assign):
        if i == len(order):
            sols.append(dict(assign))
            return
        lab = order[i]
        used = {assign[l] for l in assign if l[0] == lab[0]}
        for val in domains[lab[0]]:
            if val in used:
                continue
            assign[lab] = val
            if all(np.array_equal(out_under(k, assign, np.array(ex)), tgt)
                   for k, ex, tgt, nd in zip(known, examples, targets, need) if lab in nd and nd <= assign.keys()):
                rec(i + 1, assign)
            del assign[lab]

    rec(0, {})
    return sols


def n_injective(domain_size, k):
    return math.perm(domain_size, k)


def ideal(known, examples, world, test, items, prior_class):
    """Posterior over answer vectors under the hierarchical model ('class' vs 'none')."""
    nz = len({s for k in known for s in slots(k) if s[0] == "Z"})
    idx = np.array(items)
    mass, mass_class = {}, 0.0
    hyps = [("none", s3b.Z_WITHHELD, 1 - prior_class)] + [("class", d, prior_class / len(CLASS_DOMAINS))
                                                          for d in CLASS_DOMAINS]
    for name, dom, w in hyps:
        sols = consistent(known, examples, world, dom)
        per = w / n_injective(len(dom), nz)
        for a in sols:
            v = tuple(int(x) for x in out_under(test, a, idx))
            mass[v] = mass.get(v, 0.0) + per
            if name == "class":
                mass_class += per
    total = sum(mass.values())
    post = {v: m / total for v, m in mass.items()}
    none_answers = {tuple(int(x) for x in out_under(test, a, idx))
                    for a in consistent(known, examples, world, s3b.Z_WITHHELD)}
    modal = max(post, key=post.get)
    return {"posterior": [[list(v), p] for v, p in sorted(post.items(), key=lambda kv: -kv[1])],
            "p_class": mass_class / total, "modal": list(modal), "p_modal": post[modal],
            "n_answers_without_overhypothesis": len(none_answers)}


def random_irregular_world(rng):
    while True:
        idx = rng.choice(len(s3b.Z_WITHHELD), size=4, replace=False)
        w = [s3b.Z_WITHHELD[i] for i in idx]
        if not fits_some_split(w) and len({frozenset(p) for p in w}) == 4:
            return w


def gen(rng, p, cell):
    for _ in range(p["n_search"]):
        world = s3b.Z_STATED if cell.startswith("regular") else random_irregular_world(rng)
        known = []
        while len(known) < p["n_known"]:
            t = (int(rng.integers(4)), int(rng.integers(4)), int(rng.integers(4)))
            if t not in known:
                known.append(t)
        vals = {s for k in known for s in slots(k)}
        cands = [(l, f, z) for l in range(4) for f in range(4) for z in range(4)
                 if (l, f, z) not in known and set(slots((l, f, z))) <= vals]
        if not cands:
            continue
        test = cands[int(rng.integers(len(cands)))]
        known_ex = [[int(x) for x in rng.choice(256, size=p["n_known_examples"], replace=False)] for _ in known]
        items = [int(x) for x in rng.permutation(256)[:p["n_test_items"]]]
        idl = ideal(known, known_ex, world, test, items, p["prior_class"])
        if idl["n_answers_without_overhypothesis"] != 2:
            continue
        ok = {"regular-high": idl["p_modal"] >= p["high_min"],
              "regular-low": idl["p_modal"] <= p["low_max"],
              "irregular": idl["p_class"] < 1e-9}[cell]
        if ok:
            return {"world": world, "known": known, "known_ex": known_ex, "test": test, "items": items, "ideal": idl}
    raise RuntimeError(f"no instance for {cell}")


def build_prompt(inst, lm):
    lab = lambda t: "-".join(f"{k}{lm[k][v]}" for k, v in slots(t))
    lines = ["# Learn tasks from examples", "",
             "Each task maps an input to one of four buttons: 0, 1, 2, or 3. An input is a pair of stimuli; each "
             "stimulus has 4 binary features, written as 4 bits (bit positions 1-4, left to right). The line "
             "`1011 0110 -> 2` means: stimulus 1 is 1011, stimulus 2 is 0110, and the correct button is 2.", "",
             s3b.GRAMMAR_FLAT, "", "## Known tasks", ""]
    for k, ex in zip(inst["known"], inst["known_ex"]):
        lines.append(f"### Task {lab(k)}")
        o = out(k, inst["world"], np.array(ex))
        lines += [f"{s3b.fmt(x)} -> {int(v)}" for x, v in zip(ex, o)]
        lines.append("")
    lines += ["## The new task", "", f"You have no examples of the new task {lab(inst['test'])}.", "",
              f"Predict the button for each of these {len(inst['items'])} inputs of the new task:"]
    lines += [f"{i + 1}. {s3b.fmt(x)}" for i, x in enumerate(inst["items"])]
    lines += ["", "Reason as you like, then end with one JSON object: "
              '{"predictions": [the buttons, in order], "determined": true or false, "confidence": p}. '
              '"determined" says whether the information and examples above determine all the answers uniquely. '
              '"confidence" is your probability that all of your predictions are correct.']
    return "\n".join(lines)


def classify(preds, inst):
    """Which of the possible answer vectors Claude gave (>= 14 of 16 items), else 'neither'."""
    if preds is None:
        return None
    for rank, (v, _) in enumerate(inst["ideal"]["posterior"]):
        if sum(a == b for a, b in zip(preds, v)) >= 14:
            return "modal" if rank == 0 else f"other{rank}"
    return "neither"


def main():
    cfg = load_config()
    s3 = cfg["study3"]
    p = s3["c"]
    rng = np.random.default_rng(p["seed"])
    jobs = []
    for cell in ("regular-high", "regular-low", "irregular"):
        for i in range(p["per_cell"]):
            inst = gen(rng, p, cell)
            lm = s3b.label_maps(rng)
            jobs.append({"cell": cell, "i": i, "inst": inst, "prompt": build_prompt(inst, lm)})
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "study3c"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    with ThreadPoolExecutor(p["max_parallel"]) as ex:
        resps = list(ex.map(s3b.call, [(j["prompt"], s3["model"], s3["max_turns"], box) for j in jobs]))
    rows = []
    for j, r in zip(jobs, resps):
        inst = j["inst"]
        truth = [int(v) for v in out(inst["test"], inst["world"], np.array(inst["items"]))]
        ans = s3b.parse(r.get("result"), len(truth))
        preds = ans["predictions"] if ans else None
        choice = classify(preds, inst)
        post = dict((tuple(v), q) for v, q in inst["ideal"]["posterior"])
        chosen_ideal = (post.get(tuple(inst["ideal"]["posterior"][0][0])) if choice == "modal" else
                        post.get(tuple(inst["ideal"]["posterior"][int(choice[5:])][0])) if choice and choice.startswith("other")
                        else None)
        rows.append({"cell": j["cell"], "i": j["i"], "world": inst["world"], "known": inst["known"], "test": inst["test"],
                     "truth": truth, "truth_is_modal": truth == inst["ideal"]["modal"], "ideal": inst["ideal"],
                     "answer": ans, "choice": choice, "ideal_posterior_of_choice": chosen_ideal,
                     "claude_determined": None if ans is None else ans.get("determined"),
                     "claude_confidence": None if ans is None else ans.get("confidence"),
                     "prompt": j["prompt"], "text": r.get("result"), "cost_usd": r.get("total_cost_usd"),
                     "model_usage": list((r.get("modelUsage") or {}).keys())})
    json.dump({"config": p, "rows": rows}, open(REPO / "results" / "study3c.json", "w"), indent=1, default=str)
    summarize(rows)


def summarize(rows):
    print("cost", round(sum(r["cost_usd"] or 0 for r in rows), 2), "unparsed", sum(r["answer"] is None for r in rows))
    for cell in ("regular-high", "regular-low", "irregular"):
        rr = [r for r in rows if r["cell"] == cell and r["answer"]]
        choices = {}
        for r in rr:
            choices[r["choice"]] = choices.get(r["choice"], 0) + 1
        conf = np.mean([float(r["claude_confidence"]) for r in rr if r["claude_confidence"] is not None])
        print(f"{cell}: n={len(rr)} choices {choices} | mean confidence {conf:.2f} | says determined "
              f"{sum(bool(r['claude_determined']) for r in rr)}/{len(rr)} | ideal p(modal) "
              f"{np.mean([r['ideal']['p_modal'] for r in rr]):.2f}, p(class) {np.mean([r['ideal']['p_class'] for r in rr]):.2f}")


if __name__ == "__main__":
    main()
