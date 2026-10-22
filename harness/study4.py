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
