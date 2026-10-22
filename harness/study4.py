"""Study 4: do models discover the abstract structure (a cross-component regularity) of a compositional world?

Flat tasks with 6 symmetric X rules, 4 features (Y), and Z button pairs (button if false, button if true).
Each world carries exactly one regularity, or none:
  categorical: every Z maps FALSE into one class of 2 buttons and TRUE into the other class;
  ordinal:     every Z has its TRUE button higher than its FALSE button;
  polarity:    every X rule is false when neither bit is 1 (AND, OR, XOR).
Complementing every X rule and swapping every Z's buttons leaves every task unchanged, so without a regularity the
relative orientation of unconnected components is ambiguous; each regularity, in one consistent orientation,
resolves it. The ideal learner is hierarchical over {none, categorical, ordinal, polarity}; with colour-named
buttons, the ordinal hypothesis is unavailable (colours have no order).
"""
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import tasks

X_IN = tasks.all_inputs()
ALL = np.arange(256)
# Truth tables over (a, b) indexed 2a + b.
RULES = np.array([[0, 0, 0, 1],   # 0 both are 1
                  [0, 1, 1, 1],   # 1 at least one is 1
                  [0, 1, 1, 0],   # 2 exactly one is 1
                  [1, 0, 0, 0],   # 3 neither is 1
                  [1, 1, 1, 0],   # 4 not both are 1
                  [1, 0, 0, 1]])  # 5 both are the same
RULE_TEXT = ["both are 1", "at least one is 1", "exactly one is 1", "neither is 1", "not both are 1",
             "both are the same"]
COMPLEMENT = {0: 4, 4: 0, 1: 3, 3: 1, 2: 5, 5: 2}
POSITIVE, NEGATIVE = [0, 1, 2], [3, 4, 5]
ALL_RULES = list(range(6))
Z_ALL = [(f, t) for f in range(4) for t in range(4) if f != t]
Z_UP = [z for z in Z_ALL if z[1] > z[0]]
Z_DOWN = [z for z in Z_ALL if z[1] < z[0]]
SPLITS = [({0, 3}, {1, 2}), ({0, 1}, {2, 3}), ({0, 2}, {1, 3})]
CLASS_DOMAINS = [[(f, t) for f in sorted(a) for t in sorted(b)] for s in SPLITS for a, b in (s, s[::-1])]
TYPES = ["categorical", "ordinal", "polarity"]


def out(l, f, z, idx):
    v = RULES[l][2 * X_IN[idx, 0, f] + X_IN[idx, 1, f]]
    return np.where(v == 1, z[1], z[0])


def slots(task):
    return [("X", task[0]), ("Y", task[1]), ("Z", task[2])]


def true_out(task, world, idx=ALL):
    return out(task[0], task[1], world["Z"][task[2]], idx)


def out_under(task, assign, idx):
    return out(assign[("X", task[0])], assign[("Y", task[1])], assign[("Z", task[2])], idx)


def fits_split(pairs):
    return any(all((p[0] in a) != (p[1] in a) for p in pairs) for a, _ in SPLITS)


def ordinal_consistent(pairs):
    return all(p[1] > p[0] for p in pairs) or all(p[1] < p[0] for p in pairs)


# ---------- ideal learner ----------

def consistent_none(known, examples, world):
    """All injective label meanings consistent with every example, with no regularity (X any of 6, Z any pair)."""
    labels = sorted({s for k in known for s in slots(k)})
    domains = {"X": ALL_RULES, "Y": list(range(4)), "Z": Z_ALL}
    targets = [true_out(k, world, np.array(ex)) for k, ex in zip(known, examples)]
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


def hypotheses(colours):
    """(name, prior, list of (X domain, Z domain, sub-prior))."""
    hs = [("none", [(ALL_RULES, Z_ALL, 1.0)]),
          ("categorical", [(ALL_RULES, d, 1 / len(CLASS_DOMAINS)) for d in CLASS_DOMAINS]),
          ("polarity", [(POSITIVE, Z_ALL, 0.5), (NEGATIVE, Z_ALL, 0.5)])]
    if not colours:
        hs.append(("ordinal", [(ALL_RULES, Z_UP, 0.5), (ALL_RULES, Z_DOWN, 0.5)]))
    return [(name, 1 / len(hs), subs) for name, subs in hs]


def ideal(known, examples, world, test, items, colours, sols=None):
    sols = consistent_none(known, examples, world) if sols is None else sols
    nx = len({s for k in known for s in slots(k) if s[0] == "X"})
    nz = len({s for k in known for s in slots(k) if s[0] == "Z"})
    idx = np.array(items)
    vec = [tuple(int(v) for v in out_under(test, a, idx)) for a in sols]
    xs = [{a[l] for l in a if l[0] == "X"} for a in sols]
    zs = [{a[l] for l in a if l[0] == "Z"} for a in sols]
    mass, by_h = {}, {}
    for name, prior, subs in hypotheses(colours):
        for dx, dz, sub in subs:
            if len(dx) < nx or len(dz) < nz:      # the hypothesis cannot hold with this many distinct labels
                continue
            w = prior * sub / (math.perm(len(dx), nx) * math.perm(len(dz), nz))
            for v, xv, zv in zip(vec, xs, zs):
                if xv <= set(dx) and zv <= set(dz):
                    mass[v] = mass.get(v, 0.0) + w
                    by_h[name] = by_h.get(name, 0.0) + w
    total = sum(mass.values())
    post = sorted(((list(v), m / total) for v, m in mass.items()), key=lambda kv: -kv[1])
    return {"posterior": post, "p_modal": post[0][1], "modal": post[0][0],
            "p_hypothesis": {h: by_h.get(h, 0.0) / total for h, _, _ in hypotheses(colours)},
            "n_answers_none": len(set(vec)), "nx": nx, "nz": nz}


# ---------- worlds and instances ----------

def make_world(rng, typ, regular):
    while True:
        if regular and typ == "categorical":
            z = list(CLASS_DOMAINS[int(rng.integers(len(CLASS_DOMAINS)))])
            if ordinal_consistent(z):
                continue
            x_set = ALL_RULES
        elif regular and typ == "ordinal":
            z = [Z_UP[i] for i in rng.choice(len(Z_UP), size=4, replace=False)]
            if fits_split(z):
                continue
            x_set = ALL_RULES
        else:
            z = [Z_ALL[i] for i in rng.choice(len(Z_ALL), size=4, replace=False)]
            if fits_split(z) or ordinal_consistent(z):
                continue
            x_set = POSITIVE if (regular and typ == "polarity") else ALL_RULES
        order = rng.permutation(4)
        return {"type": typ, "regular": regular, "Z": [z[i] for i in order], "x_set": list(x_set)}


def gen_candidate(rng, typ, regular, p):
    """One random ambiguous instance (or None) with its ideal analysis under both label formats."""
    world = make_world(rng, typ, regular)
    known = []
    while len(known) < p["n_known"]:
        t = (int(rng.choice(world["x_set"])), int(rng.integers(4)), int(rng.integers(4)))
        if t not in known:
            known.append(t)
    if world["x_set"] == ALL_RULES:
        xv = {k[0] for k in known}
        if not (xv & set(POSITIVE) and xv & set(NEGATIVE)):
            return None
    vals = {s for k in known for s in slots(k)}
    cands = [(l, f, z) for l in world["x_set"] for f in range(4) for z in range(4)
             if (l, f, z) not in known and set(slots((l, f, z))) <= vals]
    if not cands:
        return None
    test = cands[int(rng.integers(len(cands)))]
    known_ex = [[int(x) for x in rng.choice(256, size=p["n_known_examples"], replace=False)] for _ in known]
    items = [int(x) for x in rng.permutation(256)[:p["n_test_items"]]]
    sols = consistent_none(known, known_ex, world)
    vecs = {tuple(int(v) for v in out_under(test, a, np.array(items))) for a in sols}
    if len(vecs) != 2:
        return None
    return {"world": world, "known": known, "known_ex": known_ex, "test": test, "items": items,
            "ideal_digits": ideal(known, known_ex, world, test, items, False, sols),
            "ideal_colours": ideal(known, known_ex, world, test, items, True, sols)}


# ---------- selection by the preregistered bands ----------

def in_band(cand, cell, typ, b):
    d, c = cand["ideal_digits"], cand["ideal_colours"]
    truth = [int(v) for v in true_out(cand["test"], cand["world"], np.array(cand["items"]))]
    if cell == "irregular":
        return d["p_modal"] <= b["irregular_max"] and c["p_modal"] <= b["irregular_max"]
    lo, hi = b[cell]
    if not (lo <= d["p_modal"] < hi and d["modal"] == truth):
        return False
    if typ == "ordinal":
        return b["ordinal_colour_range"][0] <= c["p_modal"] <= b["ordinal_colour_range"][1]
    return lo <= c["p_modal"] < hi and c["modal"] == truth


def select(rng, typ, cell, p):
    for _ in range(p["n_search"]):
        cand = gen_candidate(rng, typ, cell != "irregular", p)
        if cand is not None and in_band(cand, cell, typ, p["bands"]):
            return cand
    raise RuntimeError(f"no instance for {typ}/{cell}")


def make_instances(p, seed, plan):
    """plan: list of (type, cell, n). Returns instances with ids and colour maps, deterministically."""
    rng = np.random.default_rng(seed)
    out_list = []
    for typ, cell, n in plan:
        for i in range(n):
            inst = select(rng, typ, cell, p)
            inst.update({"id": f"{typ}-{cell}-{i:02d}", "type": typ, "cell": cell,
                         "colours": [p["colours"][int(k)] for k in rng.permutation(4)],
                         "labels": {k: [int(v) + 1 for v in rng.permutation(6 if k == "X" else 4)] for k in "XYZ"}})
            out_list.append(inst)
    return out_list


# ---------- prompts ----------

def fmt(x):
    b = format(x, "08b")
    return f"{b[:4]} {b[4:]}"


GRAMMAR = ("Every task is built from three components. A **Y component** picks one of the 4 features (bit positions "
           "1-4); the task looks at that feature in both stimuli. An **X component** is a rule on those two bits, one "
           "of: " + "; ".join(RULE_TEXT) + ". A **Z component** gives one button when the rule is true and a different "
           "button when it is false. A task's label lists its components, for example X2-Y1-Z3. Each kind has several "
           "versions (X1, X2, and so on); different versions of a kind are different from each other, and the same "
           "label always means the same component. You are not told which version does what.")


def build_prompt(inst, colours, pattern, p):
    lab = lambda t: "-".join(f"{k}{inst['labels'][k][v]}" for k, v in slots(t))
    name = (lambda b: inst["colours"][b]) if colours else (lambda b: str(b))
    buttons = ", ".join(inst["colours"][:3]) + ", or " + inst["colours"][3] if colours else "0, 1, 2, or 3"
    lines = ["# Learn tasks from examples", "",
             f"Each task maps an input to one of four buttons: {buttons}. An input is a pair of stimuli; each stimulus "
             "has 4 binary features, written as 4 bits (bit positions 1-4, left to right). The line "
             f"`1011 0110 -> {name(2)}` means: stimulus 1 is 1011, stimulus 2 is 0110, and the correct button is "
             f"{name(2)}.", "", GRAMMAR, "", "## Known tasks", ""]
    for k, ex in zip(inst["known"], inst["known_ex"]):
        lines.append(f"### Task {lab(k)}")
        o = true_out(k, inst["world"], np.array(ex))
        lines += [f"{fmt(x)} -> {name(int(v))}" for x, v in zip(ex, o)]
        lines.append("")
    lines += ["## The new task", "", f"You have no examples of the new task {lab(inst['test'])}.", "",
              f"Predict the button for each of these {len(inst['items'])} inputs of the new task:"]
    lines += [f"{i + 1}. {fmt(x)}" for i, x in enumerate(inst["items"])]
    instr = p["alternatives"] + (" " + p["pattern"] if pattern else "")
    fmt_note = "the button names as strings" if colours else "the buttons"
    lines += ["", instr, "", "Reason as you like, then end with one JSON object: "
              f'{{"predictions": [{fmt_note}, in order], "determined": true or false, "confidence": p}}. '
              '"determined" says whether the information and examples above determine all the answers uniquely. '
              '"confidence" is your probability that all of your predictions are correct.']
    return "\n".join(lines)


# ---------- running, scoring, grading ----------

GRADER = """You are coding one response from an experiment. The responder saw labelled tasks built from components (X rules, Y features, Z button pairs), had to predict a new task, and was asked to consider every assignment of meanings that fits the examples. Code the response below.

regularity_stated: the regularity the response says holds across all (or all identified) components, of a kind that could favour one assignment over another:
- "categorical": the buttons split into two groups, with one group always used for true and the other for false (for example "true is always red or blue", "true is always 1 or 2").
- "ordinal": an order relation between buttons holds across components (for example "the true button is always higher than the false button").
- "polarity": all rules share a property, such as all being false when neither bit is 1, or all being non-negated rules.
- "other": some other cross-component pattern (for example the order in which labels or rules are listed).
- "none": no cross-component regularity is stated. Saying that no pattern was found counts as "none".
If several are stated, pick the one the response relies on most.
regularity_used: true if the response uses a stated regularity to prefer one assignment or answer.
alternatives_considered: true if the response considers at least two assignments of meanings that fit the examples.

Answer only with one JSON object: {"regularity_stated": "...", "regularity_used": true or false, "alternatives_considered": true or false}

=== RESPONSE ===
"""


def call(prompt, model, max_turns, box):
    import json as _json
    import subprocess
    cmd = ["claude", "-p", prompt, "--model", model, "--tools", "", "--safe-mode", "--strict-mcp-config",
           "--no-session-persistence", "--output-format", "json", "--max-turns", str(max_turns)]
    proc = subprocess.run(cmd, cwd=box, capture_output=True, text=True, timeout=1800)
    try:
        return _json.loads(proc.stdout)
    except _json.JSONDecodeError:
        return {"result": proc.stdout, "error": proc.stderr[-500:], "returncode": proc.returncode}


def parse_answer(text, inst, colours):
    import json as _json
    decoder, found = _json.JSONDecoder(), None
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
            except _json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("predictions"), list) and len(obj["predictions"]) == len(inst["items"]):
                found = obj
    if found is None:
        return None, None
    if colours:
        inv = {c: b for b, c in enumerate(inst["colours"])}
        preds = [inv.get(str(v).strip().lower()) for v in found["predictions"]]
    else:
        preds = [int(v) if str(v).strip() in "0123" and str(v).strip() != "" else None for v in found["predictions"]]
    return found, (None if any(v is None for v in preds) else preds)


def score(inst, colours, preds, ans):
    idl = inst["ideal_colours" if colours else "ideal_digits"]
    modal = idl["modal"]
    r = None if preds is None else int(sum(a == b for a, b in zip(preds, modal)) >= 14)
    other = None if preds is None else int(any(sum(a == b for a, b in zip(preds, v)) >= 14 for v, _ in idl["posterior"][1:]))
    conf = None if ans is None or ans.get("confidence") is None else float(ans["confidence"])
    return {"R": r, "other_reading": other, "confidence": conf,
            "determined": None if ans is None else ans.get("determined"),
            "ideal_p_modal": idl["p_modal"], "ideal_p_hypothesis": idl["p_hypothesis"]}
