"""Study 3b: Claude as the learner, with an ideal-learner reference relative to what the prompt states.

Block A (ambiguity): flat tasks, labelled, 0 shots; the regularity "true -> 1 or 2, false -> 0 or 3" stated or withheld.
Block B (priority): flat tasks, unlabelled, 4 shots, regularity stated.
Block C (depth): deeper trees, labelled, 0 shots, regularity stated.
Writes results/study3b.json.
"""
import itertools
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import tasks
from env.config import load_config

X_IN = tasks.all_inputs()                      # (256, 2, 4)
LOGIC = tasks.LOGIC_TABLES
Z_STATED = [tuple(int(v) for v in row) for row in tasks.MOTOR_TABLES]          # (button if false, button if true)
Z_WITHHELD = [(f, t) for f in range(4) for t in range(4) if f != t]
LOGIC_TEXT = ["both are 1", "at least one is 1", "neither is 1", "not both are 1"]


# ---------- semantics ----------

def cond(l, f, idx):
    return LOGIC[l][2 * X_IN[idx, 0, f] + X_IN[idx, 1, f]]


def flat_out(l, f, z, idx):
    return np.where(cond(l, f, idx) == 1, z[1], z[0])


def deep_out(o, l1, f1, l2, f2, z, idx):
    b = LOGIC[o][2 * cond(l1, f1, idx) + cond(l2, f2, idx)]
    return np.where(b == 1, z[1], z[0])


ALL = np.arange(256)


# ---------- tasks as component tuples ----------
# flat task: ("flat", (l, f, m)); deep task: ("deep", (o, l1, f1, l2, f2, m)); m indexes Z_STATED (true tasks).

def true_out(task, idx=ALL):
    kind, c = task
    if kind == "flat":
        return flat_out(c[0], c[1], Z_STATED[c[2]], idx)
    return deep_out(c[0], c[1], c[2], c[3], c[4], Z_STATED[c[5]], idx)


def slots(task):
    """(label kind, true value) for each slot of a task, in display order."""
    kind, c = task
    if kind == "flat":
        return [("X", c[0]), ("Y", c[1]), ("Z", c[2])]
    return [("X", c[0]), ("X", c[1]), ("Y", c[2]), ("X", c[3]), ("Y", c[4]), ("Z", c[5])]


def out_under(task, assign, idx):
    """Responses of a task when each slot's label means assign[(kind, true value)]."""
    kind = task[0]
    v = [assign[s] for s in slots(task)]
    if kind == "flat":
        return flat_out(v[0], v[1], v[2], idx)
    return deep_out(v[0], v[1], v[2], v[3], v[4], v[5], idx)


def overlap(task, known):
    o = true_out(task)
    return max(float(np.mean(o == true_out(k))) for k in known)


# ---------- ideal learner (labelled) ----------

def consistent_assignments(known, examples, z_domain):
    """All injective label meanings consistent with every shown example. examples[i] = input indices for known[i]."""
    labels = sorted({s for k in known for s in slots(k)})
    domains = {"X": list(range(4)), "Y": list(range(4)), "Z": z_domain}
    targets = [true_out(k, np.array(ex)) for k, ex in zip(known, examples)]
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
            ok = True
            for k, ex, tgt, nd in zip(known, examples, targets, need):
                if lab in nd and all(n in assign for n in nd):
                    if not np.array_equal(out_under(k, assign, np.array(ex)), tgt):
                        ok = False
                        break
            if ok:
                rec(i + 1, assign)
            del assign[lab]

    rec(0, {})
    return sols


def ideal_labelled(known, examples, test, items, z_domain):
    sols = consistent_assignments(known, examples, z_domain)
    vecs = [tuple(int(v) for v in out_under(test, a, np.array(items))) for a in sols]
    counts = {}
    for v in vecs:
        counts[v] = counts.get(v, 0) + 1
    modal = max(counts, key=counts.get)
    return {"n_solutions": len(sols), "n_answers": len(counts), "determined": len(counts) == 1,
            "ideal_confidence": counts[modal] / len(vecs), "modal": list(modal),
            "answers": [list(v) for v in counts]}


# ---------- ideal learner (unlabelled, flat, regularity stated) ----------

FLAT64 = [("flat", tasks.task_parts(t)) for t in range(64)]


def ideal_unlabelled(known, examples, test_shots, items):
    """Candidates for each known task from its examples; the new task uses only component values of known tasks
    and is not itself a known task."""
    pool = [set(), set(), set()]
    certain = set()
    for k, ex in zip(known, examples):
        idx = np.array(ex)
        cands = [c for c in FLAT64 if np.array_equal(true_out(c, idx), true_out(k, idx))]
        for c in cands:
            for d in range(3):
                pool[d].add(c[1][d])
        if len(cands) == 1:
            certain.add(cands[0])
    sidx, tgt = np.array(test_shots[0]), np.array(test_shots[1])
    cands = [c for c in FLAT64 if c not in certain and all(c[1][d] in pool[d] for d in range(3))
             and np.array_equal(true_out(c, sidx), tgt)]
    vecs = [tuple(int(v) for v in true_out(c, np.array(items))) for c in cands]
    counts = {}
    for v in vecs:
        counts[v] = counts.get(v, 0) + 1
    modal = max(counts, key=counts.get)
    return {"n_candidates": len(cands), "n_answers": len(counts), "determined": len(counts) == 1,
            "ideal_confidence": counts[modal] / len(vecs), "modal": list(modal)}


# ---------- instance generation ----------

def random_flat(rng):
    return ("flat", (int(rng.integers(4)), int(rng.integers(4)), int(rng.integers(4))))


def random_deep(rng):
    f1, f2 = sorted(int(v) for v in rng.choice(4, size=2, replace=False))
    return ("deep", (int(rng.integers(4)), int(rng.integers(4)), f1, int(rng.integers(4)), f2, int(rng.integers(4))))


def values_of(known):
    return {s for k in known for s in slots(k)}


def sample_examples(rng, n_known, n_ex, n_shots, n_items):
    known_ex = [[int(x) for x in rng.choice(256, size=n_ex, replace=False)] for _ in range(n_known)]
    perm = rng.permutation(256)
    return known_ex, [int(x) for x in perm[:n_shots]], [int(x) for x in perm[n_shots:n_shots + n_items]]


def gen_block_a(rng, p, want):
    """want: 'det' (determined even without the regularity) or 'amb' (ambiguous without, determined with)."""
    for _ in range(p["n_search"]):
        known = []
        while len(known) < p["n_known"]:
            t = random_flat(rng)
            if t not in known:
                known.append(t)
        vals = values_of(known)
        cands = [t for t in FLAT64 if t not in known and set(slots(t)) <= vals]
        if not cands:
            continue
        test = cands[int(rng.integers(len(cands)))]
        known_ex, _, items = sample_examples(rng, len(known), p["n_known_examples"], 0, p["n_test_items"])
        stated = ideal_labelled(known, known_ex, test, items, Z_STATED)
        if not stated["determined"]:
            continue
        withheld = ideal_labelled(known, known_ex, test, items, Z_WITHHELD)
        if (want == "det") == withheld["determined"]:
            return {"known": known, "known_ex": known_ex, "test": test, "items": items, "shots": [],
                    "ideal": {"stated": stated, "withheld": withheld}}
    raise RuntimeError("block A: no instance")


def gen_block_b(rng, p, typ):
    for _ in range(p["n_search"]):
        known = []
        while len(known) < p["n_known"]:
            t = random_flat(rng)
            if t not in known:
                known.append(t)
        vals = values_of(known)
        cands = [t for t in FLAT64 if t not in known and set(slots(t)) <= vals]
        cands = [t for t in cands if (overlap(t, known) <= p["low_overlap_max"] if typ == "low"
                                      else overlap(t, known) >= p["high_overlap_min"])]
        if not cands:
            continue
        test = cands[int(rng.integers(len(cands)))]
        known_ex, shots, items = sample_examples(rng, len(known), p["n_known_examples"], p["n_shots"], p["n_test_items"])
        ideal = ideal_unlabelled(known, known_ex, (shots, true_out(test, np.array(shots))), items)
        if ideal["determined"]:
            return {"known": known, "known_ex": known_ex, "test": test, "items": items, "shots": shots,
                    "ideal": {"stated": ideal}}
    raise RuntimeError("block B: no instance")


def gen_block_c(rng, p, typ):
    pc = {**p, **p["block_c"]}
    for _ in range(pc["n_search"]):
        known = []
        while len(known) < pc["n_known"]:
            t = random_deep(rng)
            if t not in known:
                known.append(t)
        vals = values_of(known)
        for _try in range(200):
            test = random_deep(rng)
            if test in known or not set(slots(test)) <= vals:
                continue
            ov = overlap(test, known)
            if (typ == "low" and ov <= pc["low_overlap_max"]) or (typ == "high" and ov >= pc["high_overlap_min"]):
                break
        else:
            continue
        known_ex, _, items = sample_examples(rng, len(known), pc["n_known_examples"], 0, pc["n_test_items"])
        ideal = ideal_labelled(known, known_ex, test, items, Z_STATED)
        if ideal["determined"]:
            return {"known": known, "known_ex": known_ex, "test": test, "items": items, "shots": [],
                    "ideal": {"stated": ideal}}
    raise RuntimeError("block C: no instance")


# ---------- prompts ----------

def fmt(x):
    b = format(x, "08b")
    return f"{b[:4]} {b[4:]}"


def label_maps(rng):
    return {k: [int(v) + 1 for v in rng.permutation(4)] for k in "XYZ"}


def label(task, lm):
    s = [f"{k}{lm[k][v]}" for k, v in slots(task)]
    if task[0] == "flat":
        return "-".join(s)
    return f"{s[0]}({s[1]} {s[2]}, {s[3]} {s[4]}) {s[5]}"


GRAMMAR_FLAT = ("Every task is built from three components. A **Y component** picks one of the 4 features (bit "
                "positions 1-4); the task looks at that feature in both stimuli. An **X component** is a rule on those "
                "two bits, one of: both are 1; at least one is 1; neither is 1; not both are 1. A **Z component** "
                "gives one button when the rule is true and a different button when it is false. A task's label lists "
                "its components, for example X2-Y1-Z3. Each kind has several versions (X1, X2, and so on); different "
                "versions of a kind are different from each other, and the same label always means the same "
                "component. You are not told which version does what.")
GRAMMAR_DEEP = ("Every task is built from components. A **Y component** picks one of the 4 features (bit positions "
                "1-4), checked in both stimuli. An **X component** is a rule on two bits, one of: both are 1; at least "
                "one is 1; neither is 1; not both are 1. A task has two conditions, each an X rule applied to the two "
                "stimuli's values of one Y feature, giving true or false; an outer X rule then combines the two results "
                "(first condition, second condition) into true or false. A **Z component** gives one button when the "
                "outer result is true and a different button when it is false. The label X2(X1 Y3, X4 Y1) Z2 means: "
                "outer rule X2; first condition X1 on feature Y3; second condition X4 on feature Y1; buttons Z2. Each "
                "kind has several versions; different versions of a kind are different from each other, and the same "
                "label always means the same component (the same X rule can appear as an outer or inner rule). You are "
                "not told which version does what.")
GRAMMAR_UNLABELLED = ("Every task is built from three components: one of the 4 features (bit positions), checked in "
                      "both stimuli; a rule on those two bits, one of: both are 1; at least one is 1; neither is 1; not "
                      "both are 1; and a pair of buttons, one given when the rule is true and a different one when it is "
                      "false. The known tasks are named by letters only.")
REGULARITY = "For every task, the button for true is 1 or 2, and the button for false is 0 or 3."
NEW_FROM_KNOWN = ("The new task combines a feature, a rule, and a button pair that each appear somewhere among the "
                  "known tasks, in a new combination.")


def build_prompt(inst, block, regularity, lm):
    lines = ["# Learn tasks from examples", "",
             "Each task maps an input to one of four buttons: 0, 1, 2, or 3. An input is a pair of stimuli; each "
             "stimulus has 4 binary features, written as 4 bits (bit positions 1-4, left to right). The line "
             "`1011 0110 -> 2` means: stimulus 1 is 1011, stimulus 2 is 0110, and the correct button is 2.", ""]
    lines.append({"A": GRAMMAR_FLAT, "B": GRAMMAR_UNLABELLED, "C": GRAMMAR_DEEP}[block])
    if regularity:
        lines.append("")
        lines.append(REGULARITY.replace("For every task", "For every Z component") if block != "B" else REGULARITY)
    if block == "B":
        lines += ["", NEW_FROM_KNOWN]
    lines += ["", "## Known tasks", ""]
    for i, (k, ex) in enumerate(zip(inst["known"], inst["known_ex"])):
        name = chr(ord("A") + i) if block == "B" else label(k, lm)
        lines.append(f"### Task {name}")
        out = true_out(k, np.array(ex))
        lines += [f"{fmt(x)} -> {int(o)}" for x, o in zip(ex, out)]
        lines.append("")
    test = inst["test"]
    title = "the new task" if block == "B" else f"the new task {label(test, lm)}"
    lines += ["## The new task", ""]
    if inst["shots"]:
        out = true_out(test, np.array(inst["shots"]))
        lines.append(f"Here are {len(inst['shots'])} examples of {title}:")
        lines += [f"{fmt(x)} -> {int(o)}" for x, o in zip(inst["shots"], out)]
    else:
        lines.append(f"You have no examples of {title}.")
    lines += ["", f"Predict the button for each of these {len(inst['items'])} inputs of the new task:"]
    lines += [f"{i + 1}. {fmt(x)}" for i, x in enumerate(inst["items"])]
    lines += ["", "Reason as you like, then end with one JSON object: "
              '{"predictions": [the buttons, in order], "determined": true or false, "confidence": p}. '
              '"determined" says whether the information and examples above determine all the answers uniquely. '
              '"confidence" is your probability that all of your predictions are correct.']
    return "\n".join(lines)


def similarity_answers(inst, block):
    """Per item, the response of the known task most consistent with what was shown (majority over ties)."""
    test, items = inst["test"], np.array(inst["items"])
    if inst["shots"]:
        sidx = np.array(inst["shots"])
        tgt = true_out(test, sidx)
        score = [int(np.sum(true_out(k, sidx) == tgt)) for k in inst["known"]]
    else:
        ts = slots(test)
        score = [sum(a == b for a, b in zip(slots(k), ts)) for k in inst["known"]]
    top = [i for i, s in enumerate(score) if s == max(score)]
    outs = np.array([true_out(inst["known"][i], items) for i in top])
    res = []
    for j in range(len(items)):
        vals, cnt = np.unique(outs[:, j], return_counts=True)
        res.append(int(vals[np.argmax(cnt)]) if list(cnt).count(cnt.max()) == 1 else None)
    return res


# ---------- running ----------

def parse(text, n):
    decoder, found = json.JSONDecoder(), None
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("predictions"), list) and len(obj["predictions"]) == n:
                found = obj
    return found


def call(args):
    prompt, model, max_turns, box = args
    cmd = ["claude", "-p", prompt, "--model", model, "--tools", "", "--safe-mode", "--strict-mcp-config",
           "--no-session-persistence", "--output-format", "json", "--max-turns", str(max_turns)]
    proc = subprocess.run(cmd, cwd=box, capture_output=True, text=True, timeout=1800)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"result": proc.stdout, "error": proc.stderr[-500:]}


def make_jobs(cfg):
    p = cfg["study3"]["b"]
    rng = np.random.default_rng(p["seed"])
    jobs = []
    for want in ("det", "amb"):
        for i in range(p["block_a"]["per_cell"]):
            inst = gen_block_a(rng, p, want)
            lm = label_maps(rng)
            for regularity in (True, False):
                jobs.append({"block": "A", "set": want, "regularity": regularity, "i": i, "inst": inst, "lm": lm})
    for typ in ("low", "high"):
        for i in range(p["block_b"]["n_instances"]):
            inst = gen_block_b(rng, p, typ)
            jobs.append({"block": "B", "type": typ, "regularity": True, "i": i, "inst": inst, "lm": label_maps(rng)})
    for typ in ("low", "high"):
        for i in range(p["block_c"]["n_instances"]):
            inst = gen_block_c(rng, p, typ)
            jobs.append({"block": "C", "type": typ, "regularity": True, "i": i, "inst": inst, "lm": label_maps(rng)})
    return jobs


def score_job(job, resp):
    inst = job["inst"]
    truth = [int(v) for v in true_out(inst["test"], np.array(inst["items"]))]
    ideal = inst["ideal"]["stated" if job["regularity"] else "withheld"]
    ans = parse(resp.get("result"), len(truth))
    preds = ans["predictions"] if ans else None
    sim = similarity_answers(inst, job["block"])
    row = {k: v for k, v in job.items() if k not in ("inst", "lm")}
    row.update({"test": inst["test"], "known": inst["known"], "overlap": overlap(inst["test"], inst["known"]),
                "truth": truth, "similarity_answer": sim, "ideal": ideal, "answer": ans,
                "accuracy": None if preds is None else float(np.mean([a == b for a, b in zip(preds, truth)])),
                "claude_determined": None if ans is None else ans.get("determined"),
                "claude_confidence": None if ans is None else ans.get("confidence"),
                "overclaim": None if ans is None or ans.get("confidence") is None
                else float(ans["confidence"]) - ideal["ideal_confidence"],
                "text": resp.get("result"), "cost_usd": resp.get("total_cost_usd"),
                "model_usage": list((resp.get("modelUsage") or {}).keys())})
    return row


def main():
    cfg = load_config()
    s3 = cfg["study3"]
    jobs = make_jobs(cfg)
    for j in jobs:
        j["prompt"] = build_prompt(j["inst"], j["block"], j["regularity"], j["lm"])
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "study3b"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    with ThreadPoolExecutor(s3["b"]["max_parallel"]) as ex:
        resps = list(ex.map(call, [(j["prompt"], s3["model"], s3["max_turns"], box) for j in jobs]))
    rows = [score_job(j, r) for j, r in zip(jobs, resps)]
    json.dump({"config": s3, "rows": rows}, open(REPO / "results" / "study3b.json", "w"), indent=1, default=str)
    summarize(rows)


def summarize(rows):
    print("cost", round(sum(r["cost_usd"] or 0 for r in rows), 2), "unparsed", sum(r["answer"] is None for r in rows))
    cells = {}
    for r in rows:
        key = (r["block"], r.get("set") or r.get("type"), "stated" if r["regularity"] else "withheld")
        cells.setdefault(key, []).append(r)
    for key, rr in sorted(cells.items()):
        ok = [r for r in rr if r["answer"]]
        acc = np.mean([r["accuracy"] for r in ok]) if ok else float("nan")
        det_agree = np.mean([r["claude_determined"] == r["ideal"]["determined"] for r in ok]) if ok else float("nan")
        said_det = np.mean([bool(r["claude_determined"]) for r in ok]) if ok else float("nan")
        conf = np.mean([float(r["claude_confidence"]) for r in ok if r["claude_confidence"] is not None])
        ideal_conf = np.mean([r["ideal"]["ideal_confidence"] for r in ok])
        disc = [(a, s, t) for r in ok for a, s, t in zip(r["answer"]["predictions"], r["similarity_answer"], r["truth"])
                if s is not None and s != t]
        sim_share = np.mean([a == s for a, s, t in disc]) if disc else float("nan")
        print(f"{key}: n={len(ok)} accuracy {acc:.2f} | says determined {said_det:.2f} (ideal determined "
              f"{np.mean([r['ideal']['determined'] for r in ok]):.2f}), agreement {det_agree:.2f} | confidence "
              f"{conf:.2f} vs ideal {ideal_conf:.2f} | discriminating {len(disc)}, = similarity {sim_share:.2f}")


if __name__ == "__main__":
    main()
